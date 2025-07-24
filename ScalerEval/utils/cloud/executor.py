import datetime
import os
import time
from kubernetes import client, config, utils
import pytz
from kubernetes.client.rest import ApiException
import yaml
from pathlib import Path


class KubernetesClient():
    def __init__(self, 
                 config_url: str):
        self.k8s_yaml = config_url
        config.kube_config.load_kube_config(config_file=config_url)
        self.core_api = client.CoreV1Api()  # namespace, pod, service, pv, pvc
        self.apps_api = client.AppsV1Api()  # deployment
        self.scale_api = client.AutoscalingV1Api()
        self.api_client = client.ApiClient()

    ## Sanqine-add
    def list_namespaces(self):
        try:
            namespaces = self.core_api.list_namespace().items
            namespace_names = [namespace.metadata.name for namespace in namespaces]
            return namespace_names
        except ApiException as e:
            print(f"Exception when calling CoreV1Api->list_namespace: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
        
    ## Sanqine-add
    def display_namespaces(self):
        """
        Display all namespaces in a formatted output.
        """
        namespace_names = self.list_namespaces()
        #print(namespace_names)
        if namespace_names:
            print("Namespaces in the cluster:")
            for idx, namespace in enumerate(namespace_names, start=1):
                print(f"{idx}. {namespace}")
        else:
            print("No namespaces found in the cluster or failed to retrieve namespaces.")

    ## Sanqine-add
    def get_pod_info(self, namespace: str):
        pod_list = self.core_api.list_namespaced_pod(namespace=namespace)
        pod_info = {}

        # Get China timezone
        china_tz = pytz.timezone("Asia/Shanghai")

        for pod in pod_list.items:
            pod_name = pod.metadata.name
            node_name = pod.spec.node_name 
            node_ip = pod.status.host_ip 
            pod_ip = pod.status.pod_ip  
            status = pod.status.phase 

            creation_time_utc = pod.metadata.creation_timestamp
            creation_time_china = creation_time_utc.astimezone(china_tz).strftime("%Y-%m-%d %H:%M:%S")

            pod_info[pod_name] = {
                "creation_time": creation_time_china,
                "node": node_name,
                "node_ip": node_ip,
                "pod_ip": pod_ip,
                "status": status
            }

        return pod_info

    ## Sanqine-add
    def get_logs(self, pod: str, container: str, namespace: str):
        logs = self.core_api.read_namespaced_pod_log(
            name=pod,
            container=container,
            namespace=namespace,
            timestamps=True,
            pretty=True
            # since_time=start_time.isoformat() + 'Z',  # UTC format
            # limit_seconds=int((end_time - start_time).total_seconds())
        )
        return logs.split('\n')

    ## Sanqine-add
    def list_pods_in_namespace(self, namespace):
        ret = self.core_api.list_namespaced_pod(namespace)
        pods = [i.metadata.name for i in ret.items if i.metadata.name != 'loadgenerator']
        pods.sort()
        return pods
    
    ## Sanqine-add
    def get_statefulset(self, namespace: str):
        ret = self.apps_api.list_namespaced_stateful_set(namespace)
        deployments = [i.metadata.name for i in ret.items if i.metadata.name != 'loadgenerator']
        deployments.sort()
        return deployments

    
    # Get all microservices
    def get_deployments(self, namespace: str):
        ret = self.apps_api.list_namespaced_deployment(namespace)
        deployments = [i.metadata.name for i in ret.items if i.metadata.name != 'loadgenerator']
        deployments.sort()
        return deployments

    # Get stateless microservices (exclude redis, mq, mongo, db)
    def get_deployments_without_state(self, namespace: str):
        ret = self.apps_api.list_namespaced_deployment(namespace)
        def judge_state_deployment(deployment):
            state_deployments = ['redis', 'rabbitmq', 'mongo', 'mysql', 'loadgenerator', 'db', 'gateway', 'cache', 'consul', 'jaeger', 'queue']
            for state_deployment in state_deployments:
                if state_deployment in deployment:
                    return True
            return False
        deployments = [i.metadata.name for i in ret.items if not judge_state_deployment(i.metadata.name)]
        deployments.sort()
        return deployments


    def get_deployments_counts(self, namespace: str):
        dic = {}
        pod_ret=self.core_api.list_namespaced_pod(namespace, watch=False)
        deployments = self.get_deployments(namespace)
        for deployment in deployments:
            dic[deployment] = 0
            for i in pod_ret.items:
                if i.metadata.name.find(deployment)!=-1:
                    dic[deployment] = dic[deployment] + 1
        return dic

    def get_deployment_count(self, deployment: str, namespace: str):
        ret_deployment = self.apps_api.read_namespaced_deployment_scale(deployment, namespace)
        return ret_deployment.spec.replicas
    
    def get_deployments_limit(self, deployments: list, namespace: str):
        res = {}
        for deployment in deployments:
            try:
                dep_yaml = self.apps_api.read_namespaced_deployment(name=deployment, namespace=namespace)
            except:
                continue
            for container in dep_yaml.spec.template.spec.containers:
                resources = container.resources
                if resources.limits is not None:
                    res[deployment] = (resources.limits.get('cpu', None), resources.limits.get('memory', None))
                else:
                    res[deployment] = (None, None)
        return res

    # Determine the status of all service (available?)
    def all_avaliable(self, deployments: list, namespace: str):
        ret = self.apps_api.list_namespaced_deployment(namespace)
        for item in ret.items:
            if item.metadata.name in deployments and item.status.ready_replicas != item.spec.replicas:
                return False
        return True
    
    def svc_avaliable(self, svc: str, namespace: str):
        ret = self.apps_api.list_namespaced_deployment(namespace)
        for item in ret.items:
            if item.metadata.name == svc:
                if item.status.ready_replicas == item.spec.replicas:
                    return True
                else:
                    return False
        return False

    def patch_scale(self, deployment: str, count: int, namespace: str, async_req=True):
        body = {'spec': {'replicas': count}}
        self.apps_api.patch_namespaced_deployment_scale(deployment, namespace, body, async_req=async_req)

    def label_namespace(self, namespace: str, labels: dict):
        body = {
            "metadata": {
                "labels": labels
            }
        }
        try:
            api_response = self.core_api.patch_namespace(name=namespace, body=body)
            print(f"Namespace {namespace} labeled. Status: {api_response.status}")
        except ApiException as e:
            print(f"Exception when calling CoreV1Api->patch_namespace: {e}")
            return False
        return True 


    def create_from_yaml(self, deploy_path: str, namespace: str):
        path = Path(deploy_path)
        
        if path.is_dir():
            for yaml_file in path.glob("**/*.yaml"):
                print(f"Processing file: {yaml_file}")
                utils.create_from_yaml(
                    k8s_client=self.api_client,
                    yaml_file=str(yaml_file),  
                    namespace=namespace
                )
            for yaml_file in path.glob("**/*.yml"): 
                print(f"Processing file: {yaml_file}")
                utils.create_from_yaml(
                    k8s_client=self.api_client,
                    yaml_file=str(yaml_file), 
                    namespace=namespace
                )
        else:
            print(f"Processing single file: {deploy_path}")
            utils.create_from_yaml(
                k8s_client=self.api_client,
                yaml_file=deploy_path,
                namespace=namespace
            )

        
        
    def create_istio_resource(self, yaml_pth: str, namespace: str):
        with open(yaml_pth, 'r') as file:
            resources = yaml.safe_load_all(file)
            for resource in resources:
                custom_objects_api = client.CustomObjectsApi()
                group = resource['apiVersion'].split('/')[0]
                version = resource['apiVersion'].split('/')[-1]
                plural = resource['kind'].lower() + 's'
                
                try:
                    custom_objects_api.create_namespaced_custom_object(
                        group=group,
                        version=version,
                        namespace=namespace,
                        plural=plural,
                        body=resource
                    )
                    print(f"Created {resource['kind']} {resource['metadata']['name']}")
                except client.exceptions.ApiException as e:
                    print(f"Error creating {resource['kind']}: {e}")
        
    def create_namespace(self, name: str):
        new_namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=name
            )
        )
        self.core_api.create_namespace(new_namespace)
        while True:
            try:
                self.core_api.read_namespace(name=name)
                return True
            except ApiException as e:
                if e.status == 404:
                    print(f"creating namespace {name}...")
                    time.sleep(5)
                else:
                    print(f"Unexpected ApiException: {e}")
                    return False

    def delete_namespace(self, name: str):
        self.core_api.delete_namespace(name=name)
        while True:
            try:
                self.core_api.read_namespace(name=name)
                print(f'deleting namespace {name}...')
                time.sleep(5)
            except ApiException as e:
                if e.status == 404:
                    print(f"namespace {name} was deleted.")
                    return True
                else:
                    print(f"Unexpected ApiException: {e}")
                    return False
        

    def restart_deployment(self, name: str, namespace: str):
        # update `spec.template.metadata` section
        # to add `kubectl.kubernetes.io/restartedAt` annotation
        deployment = self.apps_api.read_namespaced_deployment(name=name, namespace=namespace)
        deployment.spec.template.metadata.annotations = {
            "kubectl.kubernetes.io/restartedAt": datetime.datetime.now(tz=pytz.UTC)
            .isoformat()
        }

        # patch the deployment
        self.apps_api.patch_namespaced_deployment(
            name=name, namespace=namespace, body=deployment, async_req=True
        )

    def create_default_HPA(self, 
                           namespace: str,
                           deployment: str,
                           min_replicas: int,
                           max_replicas: int,
                           cpu_th: float):
        hpa_spec = client.V1HorizontalPodAutoscaler(
            metadata=client.V1ObjectMeta(name=deployment),
            spec=client.V1HorizontalPodAutoscalerSpec(
                scale_target_ref=client.V1CrossVersionObjectReference(
                    kind="Deployment",
                    name=deployment,
                    api_version="apps/v1"
                ),
                min_replicas=min_replicas,  
                max_replicas=max_replicas,
                target_cpu_utilization_percentage=cpu_th
            )
        )

        # create horizontal scaler
        try:
            api_response = self.scale_api.create_namespaced_horizontal_pod_autoscaler(
                namespace=namespace,
                body=hpa_spec
            )
            print(f"HPA for {deployment} created. Status: {api_response.status}")
        except client.ApiException as e:
            print(f"Exception when calling AutoscalingV1Api->create_namespaced_horizontal_pod_autoscaler: {e}")

    def remove_default_HPA(self, namespace: str):
        try:
            hpa_list = self.scale_api.list_namespaced_horizontal_pod_autoscaler(namespace)
            for hpa in hpa_list.items:
                print(f"Deleting HPA: {hpa.metadata.name}")
                self.scale_api.delete_namespaced_horizontal_pod_autoscaler(
                    name=hpa.metadata.name,
                    namespace=namespace,
                    body=client.V1DeleteOptions()
                )
            print("All HPAs have been deleted.")
        except client.exceptions.ApiException as e:
            print(f"Exception when calling AutoscalingV1Api->list_namespaced_horizontal_pod_autoscaler: {e}")