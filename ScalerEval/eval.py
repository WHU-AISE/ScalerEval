import os
from base_module import init_client
from config.exp_config import Config
from functools import reduce
import pandas as pd
import time
from utils.cloud.monitor import PrometheusClient
from utils.cloud.executor import KubernetesClient
from utils import io_util

def collect_metrics(config: Config):
    kube_client: KubernetesClient
    prom_client: PrometheusClient
    prom_client, kube_client = init_client(config)
    # collect metrics
    end = int(round(time.time()))
    start = end - config.locust_exp_time
    prom_client.set_time_range(start, end, 1)
    namespace = config.benchmarks[config.select_benchmark]['namespace']

    deployments = kube_client.get_deployments(namespace)
    print(f'microservices in {namespace}: {deployments}')

    pod_df = prom_client.get_pod_num(deployments, namespace, range=True)
    qps_df = prom_client.get_complete_qps(deployments, namespace, range=True)
    metric_df = prom_client.get_metrics(deployments, namespace, range=True)
    node_metric_df = prom_client.get_node_metric(range=True)
    P50_df = prom_client.get_latency(deployments, namespace, 0.50, range=True)
    P90_df = prom_client.get_latency(deployments, namespace, 0.90, range=True)
    P95_df = prom_client.get_latency(deployments, namespace, 0.95, range=True)
    P99_df = prom_client.get_latency(deployments, namespace, 0.99, range=True)
    namespace_resource_df = prom_client.get_resource_metric(namespace, range=True)
    metric_limits = kube_client.get_deployments_limit(deployments, namespace)

    data_df = reduce(lambda left, right: pd.merge(left, right, on='timestamp'), 
                    [pod_df, qps_df, metric_df, P50_df, P90_df, P95_df, P99_df, node_metric_df, namespace_resource_df])
    
    for svc, (cpu_limit, mem_limit) in metric_limits.items():
        if cpu_limit is None:
            data_df[f'{svc}&cpu_limit'] = None
        elif 'm' in cpu_limit:
            data_df[f'{svc}&cpu_limit'] = float(cpu_limit[:-1])
        else:
            data_df[f'{svc}&cpu_limit'] = float(cpu_limit) * 1000
        
        if mem_limit is None:
            data_df[f'{svc}&mem_limit'] = None
        else:
            if 'Mi' in mem_limit:
                data_df[f'{svc}&mem_limit'] = float(mem_limit[:-2])
            elif 'Gi' in mem_limit:
                data_df[f'{svc}&mem_limit'] = float(mem_limit[:-2]) * 1024
        
    
    load_dist = config.locust_load_dist
    exp_name = config.locust_exp_name
    scaler_name = config.select_scaler
    benchmark = config.select_benchmark
    resultPath = f"tmp/{benchmark}/dist{load_dist}/{exp_name}/{scaler_name}"
    if not os.path.isdir(resultPath):
        os.makedirs(resultPath)

    data_df.to_csv(f'{resultPath}/record.csv', index=False)
    io_util.save_json(f'{resultPath}/limit.json', metric_limits)


def SLA_violation(config: Config,):
    load_dist = config.locust_load_dist
    exp_name = config.locust_exp_name
    scaler_name = config.select_scaler
    benchmark = config.select_benchmark
    SLA = config.benchmarks[benchmark]['SLA']
    resultPath = f"tmp/{benchmark}/dist{load_dist}/{exp_name}/{scaler_name}"
    result_df = pd.read_csv(f'{resultPath}/record.csv')
    return sum(result_df[result_df['istio-ingressgateway&0.9'] > SLA]['istio-ingressgateway&qps']) / sum(result_df['istio-ingressgateway&qps'])

def resource_consumption(config: Config):
    load_dist = config.locust_load_dist
    exp_name = config.locust_exp_name
    scaler_name = config.select_scaler
    benchmark = config.select_benchmark
    resultPath = f"tmp/{benchmark}/dist{load_dist}/{exp_name}/{scaler_name}"
    result_df = pd.read_csv(f'{resultPath}/record.csv')
    namespace_vCPU = [col for col in result_df.columns if col.endswith('namespace_vCPU')]
    namespace_memory = [col for col in result_df.columns if col.endswith('namespace_memory')]
    cpu_usage = result_df[namespace_vCPU].values.sum()
    mem_usage = result_df[namespace_memory].values.sum()
    return cpu_usage, mem_usage

def succ_rate(config: Config):
    load_dist = config.locust_load_dist
    exp_name = config.locust_exp_name
    scaler_name = config.select_scaler
    benchmark = config.select_benchmark
    resultPath = f"tmp/{benchmark}/dist{load_dist}/{exp_name}/{scaler_name}"
    locust_stats = pd.read_csv(f'{resultPath}/_stats.csv')
    agg_row = locust_stats[locust_stats['Name']=='Aggregated']
    succ_rate = 1-(agg_row['Failure Count'].values[0]/agg_row['Request Count'].values[0])
    return succ_rate