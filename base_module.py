import asyncio
import time
from baselines.NoneScaler.scaler import NoneScaler
from baselines.scaler_template import ScalerTemplate
from utils.cloud.executor import KubernetesClient
from utils.cloud.monitor import PrometheusClient
from config.exp_config import Config
from baselines.scaler_factory import ScalerFactory


def init_client(config: Config):
    kube_client = KubernetesClient(config.kube_config)
    prom_client = PrometheusClient(config.prom_url)
    return prom_client, kube_client


def init_env(config: Config):
    kube_client: KubernetesClient
    _, kube_client = init_client(config=config)
    # restart prometheus
    kube_client.restart_deployment(name='prometheus', namespace='istio-system')
    namespace = config.benchmarks[config.select_benchmark]['namespace']
    # deploy microservices
    deploy_path = config.benchmarks[config.select_benchmark]['deploy_path']
    istio_yml = config.benchmarks[config.select_benchmark]['istio_yaml']
    print(f'create namespace: {namespace}...')
    kube_client.create_namespace(namespace)
    # label namespace
    kube_client.label_namespace(namespace, labels={'istio-injection': 'enabled'})
    print(f'create deployments from: {deploy_path}...')
    kube_client.create_from_yaml(deploy_path, namespace)
    print(f'create virtual services from: {istio_yml}...')
    kube_client.create_istio_resource(istio_yml, namespace)
    # wait until all microservices are avaliable
    while not kube_client.all_avaliable(kube_client.get_deployments(namespace), namespace):
        print('wait until all microservices are avaliable ')
        time.sleep(5)
    print(f'all services in {namespace} are avaliable')

    time.sleep(60)
        
    


def end_env(config):
    kube_client: KubernetesClient
    _, kube_client = init_client(config=config)
    namespace = config.benchmarks[config.select_benchmark]['namespace']
    kube_client.delete_namespace(namespace)



def register_scaler(config: Config):
    scaler_name = config.select_scaler
    scaler = ScalerFactory.create_scaler(scaler_name, config)
    task = asyncio.create_task(scaler.register())
    return scaler, task