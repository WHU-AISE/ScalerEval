import re
from copy import deepcopy

import requests
import pandas as pd

class PrometheusClient:
    def __init__(self, 
                 base_url: str):
        self.prom_no_range_url = f'{base_url}/api/v1/query'
        self.prom_range_url = f'{base_url}/api/v1/query_range'


    def set_time_range(self, start: int, end: int, step: int):
        self.start = start
        self.end = end
        self.step = step

    def execute_prom(self, prom_sql, range=True):
        '''
            execute prom_sql
        '''
        if range:
            response = requests.get(self.prom_range_url,
                                    params={'query': prom_sql,
                                            'start': self.start,
                                            'end': self.end,
                                            'step': self.step})
        else:
            response = requests.get(self.prom_no_range_url,
                                    params={'query': prom_sql})
        return response.json()['data']['result']

    def get_call_latency(self, namespace, p=0.5, range=True):
        prom_sql = 'histogram_quantile(%f, sum(irate(istio_request_duration_milliseconds_bucket{reporter="destination", destination_workload_namespace="%s"}[1m])) by (destination_workload, source_workload, le))' % (p, namespace)
        responses = self.execute_prom(prom_sql, range)
        latency_df = pd.DataFrame()
        def handle(result, latency_df):
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            key =  result['metric']['source_workload'] + '_' + result['metric']['destination_workload']
            values = list(zip(*values))
            if 'timestamp' not in latency_df:
                timestamp = values[0]
                latency_df['timestamp'] = timestamp
                latency_df['timestamp'] = latency_df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            latency_df[key] = pd.Series(metric)
            latency_df[key] = latency_df[key].astype('float64')
            latency_df[key] = latency_df[key].fillna(0.0)

        [handle(result, latency_df) for result in responses]
        return latency_df
    
    
    def get_pod_num(self, deployments, namespace, range=True):
        instance_df = pd.DataFrame()
        qps_sql = 'count(kube_pod_info{namespace="%s"}) by (created_by_name)' % namespace # need kube-state-metric
        response = self.execute_prom(qps_sql, range)
        def handle(result, instance_df):
            if 'created_by_name' in result['metric']:
                pattern = r'-(?:[a-fA-F0-9]{1,})$'
                name = re.sub(pattern, '', result['metric']['created_by_name'])
                if name not in deployments:
                    return
                name = name + '&count'
                if 'values' in result.keys():
                    values = result['values']
                else:
                    values = [[result['value'][0], result['value'][1]]]
                values = list(zip(*values))
                if 'timestamp' not in instance_df:
                    timestamp = values[0]
                    instance_df['timestamp'] = timestamp
                    instance_df['timestamp'] = instance_df['timestamp'].astype('datetime64[s]')
                metric = values[1]
                instance_df[name] = pd.Series(metric)
                instance_df[name] = instance_df[name].astype('float64')

        [handle(result, instance_df) for result in response]
        return instance_df

    def get_e2e_latency(self, p=0.5, range=True):
        latency_df = pd.DataFrame()
        e2e_sql = 'histogram_quantile(%f, sum(irate(istio_request_duration_milliseconds_bucket{reporter="source",source_workload="istio-ingressgateway"}[1m])) by (source_workload,le))' % (p)
        e2e_responses = self.execute_prom(e2e_sql, range)
        def handle(result, latency_df):
            name = result['metric']['source_workload']   
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            values = list(zip(*values))
            if 'timestamp' not in latency_df:
                timestamp = values[0]
                latency_df['timestamp'] = timestamp
                latency_df['timestamp'] = latency_df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            key = name + '&' + str(p)
            latency_df[key] = pd.Series(metric)
            latency_df[key] = latency_df[key].astype('float64')
            latency_df[key] = latency_df[key].fillna(0.0)
        [handle(result, latency_df) for result in e2e_responses]
        return latency_df


    
    def get_latency(self, deployments, namespace, p=0.5, range=True):
        latency_df = pd.DataFrame()
        prom_sql = 'histogram_quantile(%f, sum(irate(istio_request_duration_milliseconds_bucket{reporter="destination", destination_workload_namespace="%s"}[1m])) by (destination_workload,le))' % (p, namespace)
        responses = self.execute_prom(prom_sql, range)
        

        e2e_sql = 'histogram_quantile(%f, sum(irate(istio_request_duration_milliseconds_bucket{reporter="source",source_workload="istio-ingressgateway"}[1m])) by (source_workload,le))' % (p)
        e2e_responses = self.execute_prom(e2e_sql, range)

        def handle(result, latency_df):
            try:
                name = result['metric']['destination_workload']
            except:
                name = result['metric']['source_workload']
            if name not in deployments and name != 'istio-ingressgateway':
                return
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            values = list(zip(*values))
            if 'timestamp' not in latency_df:
                timestamp = values[0]
                latency_df['timestamp'] = timestamp
                latency_df['timestamp'] = latency_df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            key = name + '&' + str(p)
            latency_df[key] = pd.Series(metric)
            latency_df[key] = latency_df[key].astype('float64')
            latency_df[key] = latency_df[key].fillna(0.0)

        [handle(result, latency_df) for result in responses]
        [handle(result, latency_df) for result in e2e_responses]

        return latency_df


    def get_self_latency(self, deployments, namespace, range=True):
        # get latency that excludes son's latency
        sql = 'sum by (app) (\
            label_replace(\
                (rate(istio_request_duration_milliseconds_sum{namespace="%s", reporter="destination"}[1m])) /\
                (rate(istio_request_duration_milliseconds_count{namespace="%s",reporter="destination"}[1m])),\
                "app", "$1", "destination_app", "(.*)"))\
            - sum by (app) (\
            label_replace(\
                (rate(istio_request_duration_milliseconds_sum{namespace="%s"}[1m]) or vector(0)) /\
                (rate(istio_request_duration_milliseconds_count{namespace="%s"}[1m]) or vector(1)),\
                "app", "$1", "source_app", "(.*)"))'% (namespace, namespace, namespace, namespace)
        response = self.execute_prom(sql, range)
        latency_df = pd.DataFrame()
        def handle(result, df):
            name = result['metric']['app']
            if name not in deployments:
                return
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            values = list(zip(*values))
            if 'timestamp' not in df:
                timestamp = values[0]
                df['timestamp'] = timestamp
                df['timestamp'] = df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            col = name + '&' + 'latency'
            df[col] = pd.Series(metric)
            df[col] = df[col].astype('float64')
            df[col] = df[col].fillna(0.0)
        [handle(result, latency_df) for result in response]
        return latency_df


    def get_svc_qps(self, deployments, namespace, range=True):
        '''
            Get qps for microservices
        '''
        qps_sql = 'sum(rate(istio_requests_total{reporter="destination",namespace="%s"}[1m])) by (destination_workload)' % namespace
        response = self.execute_prom(qps_sql, range)
        qps_df = pd.DataFrame()

        tmp_depoyments = deepcopy(deployments)
        def handle(result, qps_df, metric_name):
            try:
                name = result['metric']['destination_workload']
            except:
                name = result['metric']['source_workload']
            if name not in tmp_depoyments:
                return
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            values = list(zip(*values))
            if 'timestamp' not in qps_df:
                timestamp = values[0]
                qps_df['timestamp'] = timestamp
                qps_df['timestamp'] = qps_df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            col = name + '&' + metric_name
            qps_df[col] = pd.Series(metric)
            qps_df[col] = qps_df[col].astype('float64')
            qps_df[col] = qps_df[col].fillna(0.0)

        [handle(result, qps_df, 'qps') for result in response]
        return qps_df
    
    def get_complete_qps(self, deployments, namespace, range=True):
        '''
            Get qps for microservices
        '''
        qps_sql = 'sum(rate(istio_requests_total{reporter="destination",namespace="%s"}[1m])) by (destination_workload)' % namespace
        response = self.execute_prom(qps_sql, range)
        qps_df = pd.DataFrame()

        gateway_sql = 'sum(rate(istio_requests_total{reporter="source",source_workload="istio-ingressgateway"}[1m])) by (source_workload)'
        gateway_response = self.execute_prom(gateway_sql, range)

        # TCP receive
        tcp_recv_sql = 'sum(rate(istio_tcp_received_bytes_total{reporter="destination",namespace="%s"}[1m])) by (destination_workload)/1024/1024' % (
            namespace)
        # TCP sent
        tcp_sent_sql = 'sum(rate(istio_tcp_sent_bytes_total{reporter="destination",namespace="%s"}[1m])) by (destination_workload)/1024/1024' % (
            namespace)
        # TCP connection
        tcp_conn_sql = 'sum(rate(istio_tcp_connections_opened_total{reporter="destination",namespace="%s"}[1m])) by (destination_workload)' % (
            namespace)

        tcp_recv = self.execute_prom(tcp_recv_sql, range)
        tcp_sent = self.execute_prom(tcp_sent_sql, range)
        tcp_conn= self.execute_prom(tcp_conn_sql, range)

        tmp_depoyments = deepcopy(deployments)
        tmp_depoyments.append('istio-ingressgateway')

        def handle(result, qps_df, metric_name):
            try:
                name = result['metric']['destination_workload']
            except:
                name = result['metric']['source_workload']
            if name not in tmp_depoyments:
                return
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            values = list(zip(*values))
            if 'timestamp' not in qps_df:
                timestamp = values[0]
                qps_df['timestamp'] = timestamp
                qps_df['timestamp'] = qps_df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            col = name + '&' + metric_name
            qps_df[col] = pd.Series(metric)
            qps_df[col] = qps_df[col].astype('float64')
            qps_df[col] = qps_df[col].fillna(0.0)

        [handle(result, qps_df, 'qps') for result in response]
        [handle(result, qps_df, 'qps') for result in gateway_response]
        [handle(result, qps_df, 'tcp_recv') for result in tcp_recv]
        [handle(result, qps_df, 'tcp_sent') for result in tcp_sent]
        [handle(result, qps_df, 'tcp_conn') for result in tcp_conn]
        return qps_df

    def get_metrics(self, deployments, namespace, range=True):
        '''
            Get CPU,memory,fs,network for microservices
        '''
        df = pd.DataFrame()

        # CPU usage (m) note: this metric don't include the resoure of isto-proxy
        cpu_usage_sql = '(sum(rate(container_cpu_usage_seconds_total{namespace="%s",container!~\'POD|istio-proxy|\'}[1m])) by(pod)) * 1000' % (
            namespace)
        # memory usage (MB) note: this metric don't include the resoure of isto-proxy
        mem_usage_sql = 'sum(container_memory_usage_bytes{namespace="%s",container!~\'POD|istio-proxy|\'}) by(pod) / (1024*1024)' % (
            namespace)
        # CPU usage rate
        cpu_limit_sql = '(sum(container_spec_cpu_quota{namespace="%s",container!~\'POD|istio-proxy|\'}) by(pod) /100)' % (
            namespace)
        # memory usage rate
        mem_limit_sql = 'sum(container_spec_memory_limit_bytes{namespace="%s",container!~\'POD|istio-proxy|\'}) by(pod) / (1024*1024)' % (
            namespace)
        

        cpu_usage = self.execute_prom(cpu_usage_sql, range)
        mem_usage = self.execute_prom(mem_usage_sql, range)
        # cpu_limit = self.execute_prom(cpu_limit_sql, range)
        # mem_limit = self.execute_prom(mem_limit_sql, range)
        
        tempdfs = []

        def handle(result, tempdfs, col):
            name = result['metric']['pod'] + '&' + col
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            values = list(zip(*values))
            metric = values[1]
            tempdf = pd.DataFrame()
            tempdf['timestamp'] = values[0]
            tempdf[name] = pd.Series(metric)
            tempdf[name] = tempdf[name].astype('float64')
            tempdf.set_index('timestamp',inplace=True)
            tempdfs.append(tempdf)

        [handle(result, tempdfs, 'cpu_usage') for result in cpu_usage]
        [handle(result, tempdfs, 'mem_usage') for result in mem_usage]
        # [handle(result, tempdfs, 'cpu_limit') for result in cpu_limit]
        # [handle(result, tempdfs, 'mem_limit') for result in mem_limit]


        df = pd.concat(tempdfs, axis=1)
        df = df.fillna(0)

        # transform container-level metrics to service-level metrics
        final_df = pd.DataFrame()
        final_df['timestamp'] = df.index
        final_df.set_index('timestamp',inplace=True)
        col_list = list(df)
        for svc in deployments:
            cols = [col for col in col_list if col.endswith('cpu_usage') and svc==self.strip_pod_suffix(col.replace('&cpu_usage', ''))]
            final_df[svc + '&cpu_usage_mean'] = df[cols].mean(axis=1)
            final_df[svc + '&cpu_usage_max'] = df[cols].max(axis=1)
            cols = [col for col in col_list if col.endswith('mem_usage') and svc==self.strip_pod_suffix(col.replace('&mem_usage', ''))]
            final_df[svc + '&mem_usage_mean'] = df[cols].mean(axis=1)
            final_df[svc + '&mem_usage_max'] = df[cols].max(axis=1)
            # cols = [col for col in col_list if col.startswith(svc) and col.endswith('cpu_limit')]
            # final_df[svc + '&cpu_limit'] = df[cols].max(axis=1)
            # cols = [col for col in col_list if col.startswith(svc) and col.endswith('mem_limit')]
            # final_df[svc + '&mem_limit'] = df[cols].max(axis=1)


        final_df.reset_index(inplace=True)
        final_df['timestamp'] = final_df['timestamp'].astype('datetime64[s]')
        return final_df
    
    def get_node_metric(self, range=True):
        cpu_sql = '100 - (sum by (job) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100 /count by (job) (node_cpu_seconds_total{mode="idle"}))'
        cpu_response = self.execute_prom(cpu_sql, range)
        mem_sql = '(node_memory_MemTotal_bytes - node_memory_MemFree_bytes - node_memory_Buffers_bytes - node_memory_Cached_bytes) / node_memory_MemTotal_bytes * 100'
        mem_response = self.execute_prom(mem_sql, range)
        node_df = pd.DataFrame()

        def handle(result, qps_df, col):
            name = result['metric']['job']
            if 'values' in result.keys():
                values = result['values']
            else:
                values = [[result['value'][0], result['value'][1]]]
            values = list(zip(*values))
            if 'timestamp' not in qps_df:
                timestamp = values[0]
                qps_df['timestamp'] = timestamp
                qps_df['timestamp'] = qps_df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            col_name = name + '&' + col
            qps_df[col_name] = pd.Series(metric)
            qps_df[col_name] = qps_df[col_name].astype('float64')
            qps_df[col_name] = qps_df[col_name].fillna(0.0)

        [handle(result, node_df, 'node_cpu_usage') for result in cpu_response]
        [handle(result, node_df, 'node_mem_usage') for result in mem_response]
        return node_df

    def strip_pod_suffix(self, pod_name):
        # This pattern matches a hyphen followed by one or more word characters (letters, digits, and underscores)
        # at the end of the string. The pattern assumes that the deployment name does not end with a digit or letter
        # immediately before the last two hyphens.
        pattern = r'-([a-zA-Z0-9]+)$'
        
        # Remove the last part (instance identifier)
        deployment_name = re.sub(pattern, '', pod_name)
        
        # Remove the second last part (replicaset hash)
        deployment_name = re.sub(pattern, '', deployment_name)

        return deployment_name

    def get_resource_metric(self, namespace, range=True):
        metric_df = pd.DataFrame()
        vCPU_sql = 'sum(rate(container_cpu_usage_seconds_total{container!~\'POD|istio-proxy|\',namespace="%s"}[1m]))' % namespace
        mem_sql = 'sum(rate(container_memory_usage_bytes{container!~\'POD|istio-proxy|\', namespace="%s"}[1m])) / (1024*1024)' % namespace
        vCPU = self.execute_prom(vCPU_sql, range)
        mem = self.execute_prom(mem_sql, range)

        def handle(result, metric_df, col):
            values = result['values']
            values = list(zip(*values))
            if 'timestamp' not in metric_df:
                timestamp = values[0]
                metric_df['timestamp'] = timestamp
                metric_df['timestamp'] = metric_df['timestamp'].astype('datetime64[s]')
            metric = values[1]
            metric_df[col] = pd.Series(metric)
            metric_df[col] = metric_df[col].fillna(0)
            metric_df[col] = metric_df[col].astype('float64')

        [handle(result, metric_df, 'namespace_vCPU') for result in vCPU]
        [handle(result, metric_df, 'namespace_memory') for result in mem]

        return metric_df


    # def get_success_rate(self, deployments, namespace, range=True):
    #     success_df = pd.DataFrame()
    #     success_rate_sql = '(sum(rate(istio_requests_total{reporter="destination", response_code!~"5.*",namespace="%s"}[1m])) by (statefulset_kubernetes_io_pod_name, destination_workload_namespace) / sum(rate(istio_requests_total{reporter="destination",namespace="%s"}[1m])) by (statefulset_kubernetes_io_pod_name, destination_workload_namespace))' % (
    #         namespace, namespace)
    #     response = self.execute_prom(success_rate_sql, range)

    #     def handle(result, success_df):
    #         name = result['metric']['statefulset_kubernetes_io_pod_name']
    #         if name not in deployments:
    #             return
    #         values = result['values']
    #         values = list(zip(*values))
    #         if 'timestamp' not in success_df:
    #             timestamp = values[0]
    #             success_df['timestamp'] = timestamp
    #             success_df['timestamp'] = success_df['timestamp'].astype('datetime64[s]')
    #         metric = values[1]
    #         col = name + '&succ'
    #         success_df[col] = pd.Series(metric)
    #         success_df[col] = success_df[col].astype('float64')

    #     [handle(result, success_df) for result in response]

    #     return success_df