from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Body
from task_manager import TaskManager
from smart_log_solution import SmartLogFileReader, setup_smart_logging, restore_logging
from smart_log_solution import log_business_info, log_business_success, log_business_error, log_business_warning
from contextlib import asynccontextmanager
from kubernetes import client, config
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
import re
import subprocess
import pytz
import numpy as np
from contextlib import redirect_stdout, redirect_stderr
import pandas as pd
import glob
import sys
import yaml
import json
from pathlib import Path
import os
from datetime import datetime, timezone, timedelta
import time

from config.exp_config import Config
from base_module import end_env, init_client, init_env
from utils import io_util
import asyncio
import threading





# ========== Step 3: Define global state (before lifespan) ==========
environment_status = {
    "status": "idle",
    "current_step": "",
    "progress": 0,
    "config": {},
    "logs": []
}

evaluation_status = {
    "status": "idle",
    "current_step": "",
    "progress": 0,
    "config": {},
    "logs": [],
    "results": None
}

# ========== New: Status update callback functions ==========
def update_log_status(stage: str, log_entry: dict):
    """Callback function to update global log status"""
    global environment_status, evaluation_status
    
    try:
        if stage == "environment":
            environment_status["logs"].append(log_entry)
            if len(environment_status["logs"]) > 1000:
                environment_status["logs"] = environment_status["logs"][-500:]
        else:
            evaluation_status["logs"].append(log_entry)
            if len(evaluation_status["logs"]) > 1000:
                evaluation_status["logs"] = evaluation_status["logs"][-500:]
    except Exception as e:
        print(f"Error updating log status: {e}")

# ========== Step 2: Create global log readers ==========

# Create two independent log readers
env_log_reader = SmartLogFileReader("logs/pre_output.log")  # Environment log reader
eval_log_reader = SmartLogFileReader("logs/eval_output.log")  # Evaluation log reader

env_log_reader.set_status_callback(lambda stage, log_entry: update_log_status("environment", log_entry))
eval_log_reader.set_status_callback(lambda stage, log_entry: update_log_status("evaluation", log_entry))



# Global task manager
task_manager = TaskManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("logs", exist_ok=True)
    
    # 🔧 Start two log monitoring tasks
    env_log_task = asyncio.create_task(env_log_reader.start_monitoring())
    eval_log_task = asyncio.create_task(eval_log_reader.start_monitoring())
    
    yield  # Application running
    
    # On shutdown
    env_log_reader.stop_monitoring()
    eval_log_reader.stop_monitoring()
    
    env_log_task.cancel()
    eval_log_task.cancel()
    
    try:
        await env_log_task
        await eval_log_task
    except asyncio.CancelledError:
        pass

# ========== Step 5: Create FastAPI application instance ==========
app = FastAPI(lifespan=lifespan)


# Allow cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


config = Config()
prom_client, kube_client = init_client(config)


# Get all namespaces in the Kubernetes cluster
@app.get("/api/namespaces")
def get_namespaces():
    """
    Get all namespaces in the Kubernetes cluster
    :return: List of namespaces
    """
    namespaces = kube_client.list_namespaces()
    return {"namespaces": namespaces}

# Get all Pods in the specified namespace with detailed information
@app.get("/api/pods/{namespace}")
def get_pods(namespace: str):
    """
    Get all Pods in the specified namespace with detailed information
    :param namespace: Namespace name
    :return: Pod list with detailed information
    """
    try:
        # Use adapter to get basic Pod list
        pod_names = kube_client.list_pods_in_namespace(namespace)
        
        # Use adapter to get detailed information
        pod_details = []
        pod_info = kube_client.get_pod_info(namespace)
        
        for pod_name in pod_names:
            if pod_name in pod_info:
                info = pod_info[pod_name]
                
                # Get restart count (using native client)
                v1 = client.CoreV1Api()
                pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                
                restarts = 0
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        restarts += container.restart_count
                
                # Format running time
                creation_time_str = info["creation_time"]
                creation_time = datetime.strptime(creation_time_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                age = now - creation_time
                
                if age.days > 0:
                    age_str = f"{age.days}d"
                elif age.seconds // 3600 > 0:
                    age_str = f"{age.seconds // 3600}h"
                else:
                    age_str = f"{age.seconds // 60}m"
                
                pod_details.append({
                    "name": pod_name,
                    "status": info["status"],
                    "ip": info["pod_ip"] or "N/A",
                    "node": info["node"] or "N/A",
                    "restarts": restarts,
                    "age": age_str
                })
        
        return {"pods": pod_names, "podDetails": pod_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Pod list: {str(e)}")

# Get all deployments in the specified namespace with detailed information
@app.get("/api/deployments/{namespace}")
def get_deployments(namespace: str):
    """
    Get all deployments in the specified namespace with detailed information
    :param namespace: Namespace name
    :return: Deployment list with detailed information
    """
    try:
        # Directly use the new version method
        deployment_names = kube_client.get_deployments(namespace)
        
        # Get deployment detailed information
        deployment_details = []
        apps_v1 = client.AppsV1Api()
        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
        
        for deployment in deployments.items:
            if deployment.metadata.name in deployment_names:
                # Calculate deployment runtime
                if deployment.metadata.creation_timestamp:
                    creation_time = deployment.metadata.creation_timestamp
                    uptime = datetime.now(timezone.utc) - creation_time
                    if uptime.days > 0:
                        uptime_str = f"{uptime.days}d"
                    elif uptime.seconds // 3600 > 0:
                        uptime_str = f"{uptime.seconds // 3600}h"
                    else:
                        uptime_str = f"{uptime.seconds // 60}m"
                else:
                    uptime_str = "Unknown"
                
                # Get status
                status = "Active"
                if deployment.status.conditions:
                    for condition in deployment.status.conditions:
                        if condition.type == "Available" and condition.status != "True":
                            status = "NotAvailable"
                        elif condition.type == "Progressing" and condition.status != "True":
                            status = "NotProgressing"
                
                # Use adapter to check if deployment is available
                is_available = kube_client.svc_avaliable(deployment.metadata.name, namespace)
                if not is_available:
                    status = "NotReady"
                
                deployment_details.append({
                    "name": deployment.metadata.name,
                    "status": status,
                    "currentReplicas": deployment.status.ready_replicas or 0,
                    "desiredReplicas": deployment.spec.replicas,
                    "uptime": uptime_str
                })
        
        return {"deployments": deployment_names, "deploymentDetails": deployment_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment list: {str(e)}")

# Get detailed information for the specified Pod:
@app.get("/api/pod/{namespace}/{pod_name}")
def get_pod_details(namespace: str, pod_name: str):
    """
    Get detailed information for the specified Pod
    """
    try:
        pod = kube_client.core_api.read_namespaced_pod(name=pod_name, namespace=namespace)

        # Get Pod related information
        node_name = pod.spec.node_name
        node_ip = pod.status.host_ip
        pod_ip = pod.status.pod_ip
        status = pod.status.phase

        # Convert creation time to China timezone
        china_tz = pytz.timezone("Asia/Shanghai")
        creation_time_utc = pod.metadata.creation_timestamp
        creation_time_china = creation_time_utc.astimezone(china_tz).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "pod_name": pod_name,
            "namespace": namespace,
            "creation_time": creation_time_china,
            "node_name": node_name,
            "node_ip": node_ip,
            "pod_ip": pod_ip,
            "status": status
        }

    except Exception as e:
        return {"error": str(e)}

# Keep original metrics-related APIs to ensure visualization works properly
@app.get("/api/cpu_usage/{namespace}/{pod_name}")
def get_pod_cpu_usage(namespace: str, pod_name: str):
    """
    Get CPU usage for the specified Pod in the last 5 minutes
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes

        # PromQL query: get CPU usage, excluding istio-proxy and POD containers
        cpu_usage_query = f'''
        (sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by (pod)) * 1000
        '''

        # Execute PromQL query
        response = prom_client.custom_query_range(
            query=cpu_usage_query,
            start_time=start_time,
            end_time=end_time,
            step='10s'
        )

        # Process Prometheus response
        if not response:
            raise HTTPException(status_code=404, detail="CPU usage data not found")

        timestamps = []
        values = []

        # Parse Prometheus data
        for result in response:
            if 'values' in result:
                for value in result['values']:
                    timestamp = datetime.fromtimestamp(value[0], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    timestamps.append(timestamp)
                    values.append(float(value[1]))

        # Assemble return result
        return {
            "pod": pod_name,
            "namespace": namespace,
            "cpu_usage": [{"timestamp": t, "value": v} for t, v in zip(timestamps, values)]
        }

    except Exception as e:
        print(f"⚠️ CPU data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/api/namespaces/statistics")
def get_namespaces_statistics():
    """Get statistics for all namespaces"""
    try:
        namespaces = kube_client.list_namespaces()
        stats = []
        
        for namespace in namespaces:
            # Get deployment count for this namespace
            deployments = kube_client.get_deployments(namespace)
            deployment_count = len(deployments)
            
            # Get pod count for this namespace
            pods = kube_client.list_pods_in_namespace(namespace)
            pod_count = len(pods)
            
            stats.append({
                "namespace": namespace,
                "deployments": deployment_count,
                "pods": pod_count
            })
        
        return {"statistics": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get CPU and memory usage metrics for the specified Pod
@app.get("/api/metrics/{namespace}/{pod_name}")
def get_pod_metrics(namespace: str, pod_name: str):
    """
    Get CPU and memory usage metrics for the specified Pod
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)  # 10 second interval
        
        # CPU usage query
        cpu_query = f'(sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by (pod)) * 1000'
        cpu_response = prom_client.execute_prom(cpu_query, range=True)
        
        # Memory usage query
        mem_query = f'sum(container_memory_usage_bytes{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}) by(pod) / (1024*1024)'
        mem_response = prom_client.execute_prom(mem_query, range=True)
        
        # Process CPU data
        cpu_data = []
        if cpu_response:
            for result in cpu_response:
                if 'values' in result:
                    cpu_data = clean_metric_data([v[1] for v in result['values']])
        
        # Process memory data
        mem_data = []
        if mem_response:
            for result in mem_response:
                if 'values' in result:
                    mem_data = clean_metric_data([v[1] for v in result['values']])
        
        return {
            "pod": pod_name,
            "namespace": namespace,
            "cpu_usage": cpu_data,
            "memory_usage": mem_data
        }
    
    except Exception as e:
        print(f"Metrics data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# Get network traffic data for the specified Pod
@app.get("/api/network/{namespace}/{pod_name}")
def get_pod_network(namespace: str, pod_name: str):
    """
    Get network traffic data for the specified Pod
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)  # 10 second interval
        
        # Network receive traffic query (KB/s)
        receive_query = f'sum(rate(container_network_receive_bytes_total{{namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod) / 1024'
        receive_response = prom_client.execute_prom(receive_query, range=True)
        
        # Network transmit traffic query (KB/s)
        transmit_query = f'sum(rate(container_network_transmit_bytes_total{{namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod) / 1024'
        transmit_response = prom_client.execute_prom(transmit_query, range=True)
        
        # Process receive data
        receive_data = []
        if receive_response:
            for result in receive_response:
                if 'values' in result:
                    receive_data = result['values']
        
        # Process transmit data
        transmit_data = []
        if transmit_response:
            for result in transmit_response:
                if 'values' in result:
                    transmit_data = result['values']
        
        return {
            "pod": pod_name,
            "namespace": namespace,
            "network_receive": receive_data,
            "network_transmit": transmit_data
        }
    
    except Exception as e:
        print(f"⚠️ Network data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# Get latency data for the specified Pod
@app.get("/api/latency/{namespace}/{pod_name}")
def get_pod_latency(namespace: str, pod_name: str):
    """
    Get latency data for the specified Pod
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)  # 10 second interval
        

        dest_p50_sql = 'histogram_quantile(%f, sum(irate(istio_request_duration_milliseconds_bucket{reporter="destination", destination_workload_namespace="%s"}[1m])) by (pod,le))' % (0.5, namespace)
        dest_p90_sql = 'histogram_quantile(%f, sum(irate(istio_request_duration_milliseconds_bucket{reporter="destination", destination_workload_namespace="%s"}[1m])) by (pod,le))' % (0.9, namespace)
        # Target latency P50
        p50_query = f'histogram_quantile(0.5, sum(irate(istio_request_duration_milliseconds_bucket{{reporter="destination", destination_workload_namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod,le))'
        p50_response = prom_client.execute_prom(dest_p50_sql, range=True)
        
        # Target latency P90
        p90_query = f'histogram_quantile(0.9, sum(irate(istio_request_duration_milliseconds_bucket{{reporter="destination", destination_workload_namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod,le))'
        p90_response = prom_client.execute_prom(dest_p90_sql, range=True)
        
        # Process P50 data
        destP50 = []
        timestamps = []
        if p50_response:
            for result in p50_response:
                if 'values' in result:
                    # Extract timestamps and values
                    for value in result['values']:
                        if len(value) == 2:
                            # Only add values to destP50, handle timestamps separately
                            destP50.append(float(value[1]))
                            # Convert timestamp format
                            timestamp = datetime.fromtimestamp(value[0], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                            timestamps.append(timestamp)
        
        # Process P90 data
        destP90 = []
        if p90_response:
            for result in p90_response:
                if 'values' in result:
                    # Only extract values
                    destP90 = [float(value[1]) for value in result['values'] if len(value) == 2]
        
        return {
            "pod": pod_name,
            "namespace": namespace,
            "timestamps": timestamps,
            "destP50": destP50,
            "destP90": destP90
        }
    
    except Exception as e:
        print(f"⚠️ Latency data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/api/qps/{namespace}/{pod_name}")
def get_pod_qps(namespace: str, pod_name: str):
    """
    Get QPS data for the specified Pod
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)  # 10 second interval
        
        # QPS as destination
        dest_query = f'sum(rate(istio_requests_total{{reporter="destination", namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod)'
        dest_response = prom_client.execute_prom(dest_query, range=True)
        
        # QPS as source
        src_query = f'sum(rate(istio_requests_total{{reporter="source", namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod)'
        src_response = prom_client.execute_prom(src_query, range=True)
        
        # Process destination QPS data
        dest_data = []
        if dest_response:
            for result in dest_response:
                if 'values' in result:
                    dest_data = result['values']
        
        # Process source QPS data
        src_data = []
        if src_response:
            for result in src_response:
                if 'values' in result:
                    src_data = result['values']
        
        return {
            "pod": pod_name,
            "namespace": namespace,
            "destination_qps": dest_data,
            "source_qps": src_data
        }
    
    except Exception as e:
        print(f"⚠️ QPS data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/api/success_rate/{namespace}/{pod_name}")
def get_pod_success_rate(namespace: str, pod_name: str):
    """
    Get request success rate for the specified Pod
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)  # 10 second interval
        
        # Success rate query
        success_query = f'(sum(rate(istio_requests_total{{reporter="destination", response_code!~"5.*", namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod) / sum(rate(istio_requests_total{{reporter="destination", namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod))'
        success_response = prom_client.execute_prom(success_query, range=True)
        
        # Process success rate data
        success_data = []
        if success_response:
            for result in success_response:
                if 'values' in result:
                    success_data = result['values']
        
        return {
            "pod": pod_name,
            "namespace": namespace,
            "success_rate": success_data
        }
    
    except Exception as e:
        print(f"⚠️ Success rate data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/api/filesystem/{namespace}/{pod_name}")
def get_pod_filesystem(namespace: str, pod_name: str):
    """
    Get filesystem usage for the specified Pod
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)  # 10 second interval
        
        # Filesystem usage query (MB)
        usage_query = f'(sum(rate(container_fs_usage_bytes{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by(pod)) / (1024*1024)'
        usage_response = prom_client.execute_prom(usage_query, range=True)
        
        # Filesystem write query
        write_query = f'(sum(rate(container_fs_write_seconds_total{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by(pod))'
        write_response = prom_client.execute_prom(write_query, range=True)
        
        # Filesystem read query
        read_query = f'(sum(rate(container_fs_read_seconds_total{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by(pod))'
        read_response = prom_client.execute_prom(read_query, range=True)
        
        # Process usage data
        usage_data = []
        if usage_response:
            for result in usage_response:
                if 'values' in result:
                    usage_data = result['values']
        
        # Process write data
        write_data = []
        if write_response:
            for result in write_response:
                if 'values' in result:
                    write_data = result['values']
        
        # Process read data
        read_data = []
        if read_response:
            for result in read_response:
                if 'values' in result:
                    read_data = result['values']
        
        return {
            "pod": pod_name,
            "namespace": namespace,
            "fs_usage": usage_data,
            "fs_write": write_data,
            "fs_read": read_data
        }
    
    except Exception as e:
        print(f"⚠️ Filesystem data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# Fixed get_all_metrics function
@app.get("/api/all_metrics/{namespace}/{pod_name}")
def get_all_metrics(namespace: str, pod_name: str):
    """
    Get all metrics data for the specified Pod
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)
        
        print(f"Getting metrics data for {pod_name}...")
        
        # Get CPU and memory resource limits
        try:
            # Extract deployment name from pod_name
            deployment_name = prom_client.strip_pod_suffix(pod_name)
            deployments = [deployment_name]
            resource_limits = kube_client.get_deployments_limit(deployments, namespace)
        except Exception as e:
            print(f"Failed to get resource limits: {e}")
            resource_limits = {}
        
        # Format resource limits data
        formatted_limits = {}
        for svc, (cpu_limit, mem_limit) in resource_limits.items():
            formatted_limits[svc] = {
                "cpu_limit": None,
                "mem_limit": None
            }
            
            if cpu_limit:
                if 'm' in str(cpu_limit):
                    formatted_limits[svc]["cpu_limit"] = float(str(cpu_limit)[:-1])
                else:
                    formatted_limits[svc]["cpu_limit"] = float(cpu_limit) * 1000
                    
            if mem_limit:
                if 'Mi' in str(mem_limit):
                    formatted_limits[svc]["mem_limit"] = float(str(mem_limit)[:-2])
                elif 'Gi' in str(mem_limit):
                    formatted_limits[svc]["mem_limit"] = float(str(mem_limit)[:-2]) * 1024
        
        # Manually build complete metrics data, using old version logic
        metrics_json = {
            "pod": pod_name,
            "namespace": namespace,
            "timestamps": [],
            "metrics": {},
            "resource_limits": formatted_limits
        }
        
        # Manually get various metrics, emulating old version's complete metric set
        try:
            # 1. CPU usage
            cpu_query = f'(sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by (pod)) * 1000'
            cpu_response = prom_client.execute_prom(cpu_query, range=True)
            
            # 2. Memory usage
            mem_query = f'sum(container_memory_usage_bytes{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}) by(pod) / (1024*1024)'
            mem_response = prom_client.execute_prom(mem_query, range=True)
            
            # 3. Network receive
            net_receive_query = f'sum(rate(container_network_receive_bytes_total{{namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod) / 1024'
            net_receive_response = prom_client.execute_prom(net_receive_query, range=True)
            
            # 4. Network transmit
            net_transmit_query = f'sum(rate(container_network_transmit_bytes_total{{namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod) / 1024'
            net_transmit_response = prom_client.execute_prom(net_transmit_query, range=True)
            
            # 5. Latency P50
            dest_p50_query = f'histogram_quantile(0.5, sum(irate(istio_request_duration_milliseconds_bucket{{reporter="destination", destination_workload_namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod,le))'
            dest_p50_response = prom_client.execute_prom(dest_p50_query, range=True)
            
            # 6. Latency P90
            dest_p90_query = f'histogram_quantile(0.9, sum(irate(istio_request_duration_milliseconds_bucket{{reporter="destination", destination_workload_namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod,le))'
            dest_p90_response = prom_client.execute_prom(dest_p90_query, range=True)
            
            # 7. Destination QPS
            dest_qps_query = f'sum(rate(istio_requests_total{{reporter="destination", namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod)'
            dest_qps_response = prom_client.execute_prom(dest_qps_query, range=True)
            
            # 8. Source QPS
            src_qps_query = f'sum(rate(istio_requests_total{{reporter="source", namespace="{namespace}", pod="{pod_name}"}}[1m])) by (pod)'
            src_qps_response = prom_client.execute_prom(src_qps_query, range=True)
            
            # 9. Filesystem usage
            fs_usage_query = f'(sum(rate(container_fs_usage_bytes{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by(pod)) / (1024*1024)'
            fs_usage_response = prom_client.execute_prom(fs_usage_query, range=True)
            
            # 10. Filesystem write
            fs_write_query = f'(sum(rate(container_fs_write_seconds_total{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by(pod))'
            fs_write_response = prom_client.execute_prom(fs_write_query, range=True)
            
            # 11. Filesystem read
            fs_read_query = f'(sum(rate(container_fs_read_seconds_total{{namespace="{namespace}", pod="{pod_name}", container!~"POD|istio-proxy"}}[1m])) by(pod))'
            fs_read_response = prom_client.execute_prom(fs_read_query, range=True)
            
            # Process timestamps - get from first response with data
            timestamp_set = False
            
            def process_response(response, metric_name):
                nonlocal timestamp_set
                if response:
                    for result in response:
                        if 'values' in result and result['values']:
                            values = result['values']
                            
                            # Set timestamps (only once)
                            if not timestamp_set:
                                timestamps = []
                                for value in values:
                                    timestamp = datetime.fromtimestamp(value[0], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                                    timestamps.append(timestamp)
                                metrics_json["timestamps"] = timestamps
                                timestamp_set = True
                            
                            # Process metrics data
                            metric_values = []
                            for value in values:
                                val = float(value[1])
                                if pd.isna(val) or not np.isfinite(val):
                                    metric_values.append(0.0)
                                else:
                                    metric_values.append(val)
                            
                            metrics_json["metrics"][metric_name] = metric_values
                            break  # Only process first matching result
            
            # Process all responses
            process_response(cpu_response, "cpu_usage")
            process_response(mem_response, "mem_usage")
            process_response(net_receive_response, "net_receive")
            process_response(net_transmit_response, "net_trainsmit")  # Note: keep original typo for frontend compatibility
            process_response(dest_p50_response, "destP50")
            process_response(dest_p90_response, "destP90")
            process_response(dest_qps_response, "dest_qps")
            process_response(src_qps_response, "src_qps")
            process_response(fs_usage_response, "fs_usage")
            process_response(fs_write_response, "fs_write")
            process_response(fs_read_response, "fs_read")
            
            print(f"Successfully got {len(metrics_json['metrics'])} metrics")
            
        except Exception as e:
            print(f"Failed to get metrics data: {e}")
            # Provide empty data instead of failure
            import traceback
            traceback.print_exc()
        
        return metrics_json
    
    except Exception as e:
        print(f"⚠️ All metrics data query failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# You can also add a generic data cleaning function
def clean_metric_data(data):
    """
    Clean metrics data, remove NaN and infinite values
    """
    if isinstance(data, list):
        cleaned_data = []
        for value in data:
            if pd.isna(value) or not np.isfinite(value):
                cleaned_data.append(0.0)
            else:
                cleaned_data.append(float(value))
        return cleaned_data
    elif isinstance(data, pd.Series):
        return data.fillna(0.0).replace([float('inf'), float('-inf')], 0.0).tolist()
    else:
        return data

@app.get("/api/node_metrics")
def get_node_metrics():
    """
    Get node-level metrics
    """
    try:
        end_time = time.time()
        start_time = end_time - 300  # Past 5 minutes of data
        prom_client.set_time_range(start_time, end_time, 10)
        
        # Get node metrics
        node_metrics = prom_client.get_node_metric(range=True)
        
        # Convert DataFrame to JSON-friendly format
        metrics_json = {
            "timestamps": node_metrics['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            "nodes": {}
        }
        
        # Extract data for each node
        for column in node_metrics.columns:
            if column != 'timestamp':
                # Column format: node_name&metric_type
                parts = column.split('&')
                if len(parts) == 2:
                    node_name = parts[0]
                    metric_type = parts[1]
                    
                    if node_name not in metrics_json["nodes"]:
                        metrics_json["nodes"][node_name] = {}
                        
                    metrics_json["nodes"][node_name][metric_type] = node_metrics[column].tolist()
        
        return metrics_json
    
    except Exception as e:
        print(f"⚠️ Node metrics data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# New API endpoints
@app.get("/api/yaml/namespace/{namespace}")
def get_namespace_yaml(namespace: str):
    """
    Get YAML definition for the specified namespace
    """
    try:
        v1 = client.CoreV1Api()
        ns = v1.read_namespace(namespace)
        
        # Convert Kubernetes object to dict, then to YAML
        ns_dict = client.ApiClient().sanitize_for_serialization(ns)
        yaml_str = yaml.dump(ns_dict, default_flow_style=False)
        
        return {"yaml": yaml_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get namespace YAML: {str(e)}")

@app.get("/api/yaml/deployment/{namespace}/{name}")
def get_deployment_yaml(namespace: str, name: str):
    """
    Get YAML definition for the specified deployment
    """
    try:
        apps_v1 = client.AppsV1Api()
        deployment = apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
        
        # Convert Kubernetes object to dict, then to YAML
        deployment_dict = client.ApiClient().sanitize_for_serialization(deployment)
        yaml_str = yaml.dump(deployment_dict, default_flow_style=False)
        
        return {"yaml": yaml_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment YAML: {str(e)}")

@app.get("/api/yaml/pod/{namespace}/{name}")
def get_pod_yaml(namespace: str, name: str):
    """
    Get YAML definition for the specified Pod
    """
    try:
        v1 = client.CoreV1Api()
        pod = v1.read_namespaced_pod(name=name, namespace=namespace)
        
        # Convert Kubernetes object to dict, then to YAML
        pod_dict = client.ApiClient().sanitize_for_serialization(pod)
        yaml_str = yaml.dump(pod_dict, default_flow_style=False)
        
        return {"yaml": yaml_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Pod YAML: {str(e)}")

@app.post("/api/deployment/restart/{namespace}/{name}")
def restart_deployment(namespace: str, name: str):
    """
    Restart the specified Deployment
    """
    try:
        # Directly use the new version method
        kube_client.restart_deployment(name=name, namespace=namespace)
        return {"message": f"Deployment {name} restarted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart deployment: {str(e)}")

@app.post("/api/deployment/scale/{namespace}/{name}")
def scale_deployment(namespace: str, name: str, data: Dict[str, int] = Body(...)):
    """
    Adjust the replica count of the Deployment
    """
    try:
        replicas = data.get("replicas")
        if replicas is None:
            raise HTTPException(status_code=400, detail="Please provide replicas field")
        
        # Directly use the new version method
        kube_client.patch_scale(deployment=name, count=replicas, namespace=namespace, async_req=False)
        
        return {"message": f"Deployment {name} replica count set to {replicas}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set replica count: {str(e)}")

@app.post("/api/deployment/create/{namespace}")
def create_deployment(namespace: str, data: Dict[str, Any] = Body(...)):
    """
    Create Deployment through form
    """
    try:
        name = data.get("name")
        image = data.get("image")
        replicas = data.get("replicas", 1)
        port = data.get("port", 80)
        
        if not name or not image:
            raise HTTPException(status_code=400, detail="Please provide name and image fields")
        
        # Create deployment definition
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": name,
                "namespace": namespace
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": {
                        "app": name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": name
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": name,
                                "image": image,
                                "ports": [
                                    {
                                        "containerPort": port
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
        
        # Create temporary YAML file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as temp:
            yaml.dump(deployment, temp)
            temp_path = temp.name
        
        # Try to use new version method to create deployment
        try:
            # New version method name is create_from_yaml
            kube_client.create_from_yaml(deploy_path=temp_path, namespace=namespace)
        except AttributeError:
            # If new method doesn't exist, try old method name
            try:
                kube_client.apply_yaml(yaml_path=temp_path, namespace=namespace)
            except AttributeError:
                # If both don't exist, use native client
                import os
                with open(temp_path, 'r') as f:
                    yaml_content = yaml.safe_load(f)
                apps_v1 = client.AppsV1Api()
                apps_v1.create_namespaced_deployment(namespace=namespace, body=yaml_content)
        
        # Delete temporary file
        try:
            import os
            os.unlink(temp_path)
        except:
            pass
        
        return {"message": f"Deployment {name} created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create deployment: {str(e)}")

@app.post("/api/deployment/create-from-yaml/{namespace}")
def create_deployment_from_yaml(namespace: str, data: Dict[str, str] = Body(...)):
    """
    Create Deployment through YAML
    """
    try:
        yaml_str = data.get("yaml")
        if not yaml_str:
            raise HTTPException(status_code=400, detail="Please provide YAML")
        
        # Parse YAML
        try:
            deployment = yaml.safe_load(yaml_str)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"YAML parsing failed: {str(e)}")
        
        # Ensure namespace is correct
        deployment["metadata"]["namespace"] = namespace
        
        # Create temporary YAML file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as temp:
            yaml.dump(deployment, temp)
            temp_path = temp.name
        
        # Try to use new version method to create deployment
        try:
            # New version method name is create_from_yaml
            kube_client.create_from_yaml(deploy_path=temp_path, namespace=namespace)
        except AttributeError:
            # If new method doesn't exist, try old method name
            try:
                kube_client.apply_yaml(yaml_path=temp_path, namespace=namespace)
            except AttributeError:
                # If both don't exist, use native client
                apps_v1 = client.AppsV1Api()
                apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        
        # Delete temporary file
        try:
            import os
            os.unlink(temp_path)
        except:
            pass
        
        return {"message": f"Deployment created from YAML successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create deployment: {str(e)}")

@app.delete("/api/pod/{namespace}/{name}")
def delete_pod(namespace: str, name: str):
    """
    Delete the specified Pod
    """
    try:
        # Use native client to delete Pod
        v1 = client.CoreV1Api()
        v1.delete_namespaced_pod(name=name, namespace=namespace)
        return {"message": f"Pod {name} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Pod: {str(e)}")

@app.get("/api/pod/containers/{namespace}/{name}")
def get_pod_containers(namespace: str, name: str):
    """
    Get list of containers in the Pod
    """
    try:
        v1 = client.CoreV1Api()
        pod = v1.read_namespaced_pod(name=name, namespace=namespace)
        
        containers = []
        for container in pod.spec.containers:
            containers.append(container.name)
        
        return {"containers": containers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container list: {str(e)}")

@app.get("/api/pod/logs/{namespace}/{name}")
def get_pod_logs(namespace: str, name: str, container: Optional[str] = None, lines: int = 100):
    """
    Get logs for the specified container in the Pod
    """
    try:
        # If no container specified, get the first container
        if not container or container == "default":
            v1 = client.CoreV1Api()
            pod = v1.read_namespaced_pod(name=name, namespace=namespace)
            container = pod.spec.containers[0].name
        
        # Use adapter to get logs
        logs = kube_client.get_logs(pod=name, container=container, namespace=namespace)
        
        # Limit the number of returned lines
        if lines and lines < len(logs):
            logs = logs[-lines:]
        
        return {"logs": "\n".join(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

# Add cluster overview API
@app.get("/api/cluster/overview")
def get_cluster_overview():
    """
    Get cluster overview information: node count, namespace count, Pod count, etc.
    """
    try:
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        
        # Get node information
        nodes = v1.list_node()
        node_count = len(nodes.items)
        
        # Node health status
        ready_nodes = 0
        for node in nodes.items:
            for condition in node.status.conditions:
                if condition.type == "Ready" and condition.status == "True":
                    ready_nodes += 1
                    break
        
        # Use adapter to get namespace information
        namespaces = kube_client.list_namespaces()
        namespace_count = len(namespaces)
        
        # Get count of all resources
        all_pods = v1.list_pod_for_all_namespaces(watch=False)
        all_deployments = apps_v1.list_deployment_for_all_namespaces(watch=False)
        all_services = v1.list_service_for_all_namespaces(watch=False)
        
        # Pod status statistics
        pod_status = {
            "Running": 0,
            "Pending": 0,
            "Failed": 0,
            "Succeeded": 0,
            "Unknown": 0
        }
        
        for pod in all_pods.items:
            status = pod.status.phase
            if status in pod_status:
                pod_status[status] += 1
            else:
                pod_status["Unknown"] += 1
        
        # Organize return data
        return {
            "nodes": {
                "total": node_count,
                "ready": ready_nodes
            },
            "namespaces": namespace_count,
            "resources": {
                "pods": len(all_pods.items),
                "deployments": len(all_deployments.items),
                "services": len(all_services.items)
            },
            "pod_status": pod_status
        }
    
    except Exception as e:
        print(f"⚠️ Failed to get cluster overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cluster overview: {str(e)}")

# Get service list
@app.get("/api/services/{namespace}")
def get_services(namespace: str):
    try:
        v1 = client.CoreV1Api()
        services = v1.list_namespaced_service(namespace=namespace)
        
        service_details = []
        for service in services.items:
            # Get service type
            service_type = service.spec.type
            
            # Get service ports
            ports = []
            if service.spec.ports:
                for port in service.spec.ports:
                    port_info = {
                        "name": port.name,
                        "port": port.port,
                        "target_port": port.target_port,
                        "protocol": port.protocol
                    }
                    if port.node_port:
                        port_info["node_port"] = port.node_port
                    ports.append(port_info)
            
            # Get service selectors
            selectors = service.spec.selector if service.spec.selector else {}
            
            # Get cluster IP
            cluster_ip = service.spec.cluster_ip
            external_ip = None
            
            # Get external IP (LoadBalancer type)
            if service_type == "LoadBalancer" and service.status.load_balancer.ingress:
                for ingress in service.status.load_balancer.ingress:
                    external_ip = ingress.ip or ingress.hostname
                    break
            
            # Calculate running time
            creation_time = service.metadata.creation_timestamp
            uptime = datetime.now(timezone.utc) - creation_time
            if uptime.days > 0:
                uptime_str = f"{uptime.days}d"
            elif uptime.seconds // 3600 > 0:
                uptime_str = f"{uptime.seconds // 3600}h"
            else:
                uptime_str = f"{uptime.seconds // 60}m"
            
            service_details.append({
                "name": service.metadata.name,
                "type": service_type,
                "cluster_ip": cluster_ip,
                "external_ip": external_ip,
                "ports": ports,
                "selectors": selectors,
                "age": uptime_str
            })
        
        return {"services": service_details}
    
    except Exception as e:
        print(f"Failed to get service list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service list: {str(e)}")






################################################################################
# Sanqine ElasticScaling api
@app.get("/api/scaler-eval/benchmarks")
def get_available_benchmarks():
    """Get real benchmark configurations based on config.exp_config.Config"""
    try:
        from config.exp_config import Config
        config = Config()
        
        benchmarks = []
        for bench_name, bench_config in config.benchmarks.items():
            display_name_mapping = {
                "online-boutique": "Online Boutique",
                "sockshop": "Sock Shop",
                "hipster": "Online Boutique (Hipster)"
            }
            
            display_name = display_name_mapping.get(bench_name, bench_name.replace('-', ' ').title())
            
            benchmarks.append({
                "name": bench_name,
                "display_name": display_name,
                "description": f"Microservices demo - {display_name}",
                "namespace": bench_config['namespace'],
                "entry": bench_config['entry'],
                "sla": bench_config['SLA'],
                "deploy_path": bench_config.get('deploy_path', ''),
                "istio_yaml": bench_config.get('istio_yaml', '')
            })
        
        return {"benchmarks": benchmarks}
    except Exception as e:
        print(f"Error loading benchmarks: {e}")
        return {
            "benchmarks": [
                {
                    "name": "online-boutique",
                    "display_name": "Online Boutique",
                    "description": "Google's microservices demo - e-commerce platform",
                    "namespace": "online-boutique",
                    "sla": 500
                },
                {
                    "name": "sockshop", 
                    "display_name": "Sock Shop",
                    "description": "Weaveworks' microservices demo - sock store",
                    "namespace": "sockshop",
                    "sla": 500
                }
            ]
        }

@app.get("/api/scaler-eval/scalers")
def get_available_scalers():
    """Get scaler list based on real baselines directory"""
    try:
        baselines_dir = "./baselines"
        scalers = []
        
        scalers.append({
            "name": "None",
            "display_name": "No Scaler",
            "description": "Baseline without auto-scaling",
            "type": "baseline"
        })
        
        known_scalers = {
            "KHPA": [
                {
                    "name": "KHPA-20",
                    "display_name": "KHPA (20% CPU)",
                    "description": "Kubernetes HPA with 20% CPU threshold",
                    "type": "reactive"
                },
                {
                    "name": "KHPA-50", 
                    "display_name": "KHPA (50% CPU)",
                    "description": "Kubernetes HPA with 50% CPU threshold",
                    "type": "reactive"
                },
                {
                    "name": "KHPA-80",
                    "display_name": "KHPA (80% CPU)", 
                    "description": "Kubernetes HPA with 80% CPU threshold",
                    "type": "reactive"
                }
            ],
            "Showar": [{
                "name": "Showar",
                "display_name": "Showar",
                "description": "Research-based predictive auto-scaler",
                "type": "predictive"
            }],
            "PBScaler": [{
                "name": "PBScaler", 
                "display_name": "PBScaler",
                "description": "Performance-based scaler",
                "type": "performance"
            }],
            "NonScaler": [{
                "name": "NonScaler",
                "display_name": "Non Scaler",
                "description": "Non-scaling baseline",
                "type": "baseline"
            }]
        }
        
        if os.path.exists(baselines_dir):
            for item in os.listdir(baselines_dir):
                item_path = os.path.join(baselines_dir, item)
                if os.path.isdir(item_path) and not item.startswith('_') and not item.startswith('.'):
                    if item in known_scalers:
                        scalers.extend(known_scalers[item])
                    else:
                        scalers.append({
                            "name": item,
                            "display_name": item,
                            "description": f"Custom scaler: {item}",
                            "type": "custom"
                        })
        else:
            for scaler_list in known_scalers.values():
                scalers.extend(scaler_list)
        
        return {"scalers": scalers}
        
    except Exception as e:
        print(f"Error scanning scalers: {e}")
        return {
            "scalers": [
                {"name": "None", "display_name": "No Scaler", "description": "Baseline without auto-scaling", "type": "baseline"},
                {"name": "KHPA-20", "display_name": "KHPA (20% CPU)", "description": "Kubernetes HPA with 20% CPU threshold", "type": "reactive"},
                {"name": "KHPA-50", "display_name": "KHPA (50% CPU)", "description": "Kubernetes HPA with 50% CPU threshold", "type": "reactive"},
                {"name": "KHPA-80", "display_name": "KHPA (80% CPU)", "description": "Kubernetes HPA with 80% CPU threshold", "type": "reactive"},
                {"name": "Showar", "display_name": "Showar", "description": "Research-based auto-scaler", "type": "predictive"},
                {"name": "PBScaler", "display_name": "PBScaler", "description": "Performance-based scaler", "type": "performance"}
            ]
        }

@app.get("/api/scaler-eval/workloads")
def get_available_workloads():
    """Get workload configurations based on real load directory structure"""
    try:
        workloads = []
        load_distributions = [
            {"value": "1", "label": "Light Load"},
            {"value": "2", "label": "Medium Load"}, 
            {"value": "3", "label": "Heavy Load"}
        ]
        
        known_workloads = {
            "wiki": {
                "display_name": "Wiki Workload",
                "description": "Wikipedia-like access pattern with browsing and interaction flows",
                "supports_load_dist": True
            }
        }
        
        load_base_dir = "./load"
        found_workloads = set()
        
        if os.path.exists(load_base_dir):
            for benchmark_dir in os.listdir(load_base_dir):
                benchmark_path = os.path.join(load_base_dir, benchmark_dir)
                if os.path.isdir(benchmark_path):
                    locustfiles = glob.glob(os.path.join(benchmark_path, "*_locustfile.py"))
                    
                    for locustfile in locustfiles:
                        filename = os.path.basename(locustfile)
                        workload_name = filename.replace("_locustfile.py", "")
                        found_workloads.add(workload_name)
        
        for workload_name in found_workloads:
            if workload_name in known_workloads:
                workload_info = known_workloads[workload_name]
                workloads.append({
                    "name": workload_name,
                    "display_name": workload_info["display_name"],
                    "description": workload_info["description"],
                    "duration_options": [300, 600, 900, 1200, 1800],
                    "supports_load_dist": workload_info.get("supports_load_dist", True)
                })
            else:
                workloads.append({
                    "name": workload_name,
                    "display_name": workload_name.replace("_", " ").title(),
                    "description": f"{workload_name.title()}-like access pattern",
                    "duration_options": [300, 600, 900, 1200, 1800],
                    "supports_load_dist": True
                })
        
        if not workloads:
            workloads = [
                {
                    "name": "wiki",
                    "display_name": "Wiki Workload", 
                    "description": "Wikipedia-like access pattern",
                    "duration_options": [300, 600, 900, 1200, 1800],
                    "supports_load_dist": True
                }
            ]
        
        return {
            "workloads": workloads,
            "load_distributions": load_distributions
        }
        
    except Exception as e:
        print(f"Error scanning workloads: {e}")
        return {
            "workloads": [
                {
                    "name": "wiki",
                    "display_name": "Wiki Workload",
                    "description": "Wikipedia-like access pattern", 
                    "duration_options": [300, 600, 900, 1200, 1800],
                    "supports_load_dist": True
                }
            ],
            "load_distributions": [
                {"value": "1", "label": "Light Load"},
                {"value": "2", "label": "Medium Load"},
                {"value": "3", "label": "Heavy Load"}
            ]
        }


# Environment preparation phase API
@app.post("/api/scaler-eval/prepare-environment")
async def prepare_environment(config: Dict = Body(...)):
    """Phase 1: Prepare environment"""
    global environment_status
    
    if environment_status["status"] == "preparing":
        raise HTTPException(status_code=400, detail="Environment is already being prepared")
    
    required_fields = ["benchmark", "scaler"]
    for field in required_fields:
        if field not in config:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    environment_status.update({
        "status": "preparing",
        "current_step": "Initializing environment",
        "progress": 0,
        "config": config,
        "logs": []
    })
    
    # Create background task
    task = asyncio.create_task(run_environment_preparation_safe(config))
    task_manager.add_task(task)
    
    return {"message": "Environment preparation started"}


async def run_environment_preparation_safe(config: Dict):
    """Safe environment preparation process"""
    global environment_status
    
    original_stdout = None
    original_stderr = None
    log_file = None
    
    try:
        # Use smart logging setup, will filter LogFileReader debug output
        original_stdout, original_stderr, log_file = setup_smart_logging("logs/pre_output.log")
        
        # Use business log functions, these will be displayed in frontend
        log_business_info("Starting environment preparation with config: {}".format(config), "Environment")
        log_business_info("Benchmark: {}, Scaler: {}".format(config['benchmark'], config['scaler']), "Environment")
        
        # Import necessary modules
        from base_module import end_env, init_env
        from config.exp_config import Config
        
        # Create config object
        eval_config = Config()
        eval_config.select_benchmark = config["benchmark"]
        eval_config.select_scaler = config["scaler"]
        
        # Step 1: Pre-clean environment
        environment_status["current_step"] = "Pre-cleaning environment"
        environment_status["progress"] = 10
        log_business_info("Step 1: Pre-cleaning environment to avoid conflicts", "Environment")
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, end_env, eval_config)
            log_business_success("Pre-cleaning completed successfully", "Environment")
        except Exception as cleanup_error:
            log_business_warning("Pre-cleaning warning: {}".format(str(cleanup_error)), "Environment")
        
        log_business_info("Waiting for resources to be fully cleaned...", "Environment")
        await asyncio.sleep(10)
        
        # Step 2: Initialize environment
        environment_status["current_step"] = f"Initializing {config['benchmark']} microservices"
        environment_status["progress"] = 50
        log_business_info("Step 2: Starting initialization for benchmark: {}".format(config['benchmark']), "Environment")
        
        await loop.run_in_executor(None, init_env, eval_config)
        log_business_success("Environment initialization completed successfully", "Environment")
        
        # Step 3: Verify environment readiness
        environment_status["current_step"] = "Verifying environment readiness"
        environment_status["progress"] = 90
        log_business_info("Step 3: Verifying all services are ready", "Environment")
        
        await asyncio.sleep(5)
        
        # Complete
        environment_status["status"] = "ready"
        environment_status["current_step"] = "Environment ready for evaluation"
        environment_status["progress"] = 100
        log_business_success("Environment preparation completed successfully!", "Environment")
        
    except asyncio.CancelledError:
        log_business_warning("Environment preparation was cancelled", "Environment")
        environment_status["status"] = "idle"
        environment_status["current_step"] = "Cancelled"
        raise
    except Exception as e:
        log_business_error("Environment preparation failed: {}".format(str(e)), "Environment")
        import traceback
        traceback.print_exc()
        
        environment_status["status"] = "error"
        environment_status["current_step"] = f"Environment preparation failed: {str(e)}"
        
    finally:
        # Restore output
        if original_stdout and original_stderr and log_file:
            restore_logging(original_stdout, original_stderr, log_file)


# Evaluation execution API
@app.post("/api/scaler-eval/start-evaluation")
async def start_evaluation(config: Dict = Body(...)):
    """Phase 2: Start evaluation - simplified configuration"""
    global evaluation_status, environment_status
    
    if environment_status["status"] != "ready":
        raise HTTPException(status_code=400, detail="Environment is not ready. Please prepare environment first.")
    
    if evaluation_status["status"] == "running":
        raise HTTPException(status_code=400, detail="Evaluation is already running")
    
    # 🔧 Simplified required field validation
    required_fields = ["workload"]
    for field in required_fields:
        if field not in config:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # 🔧 Use predefined configuration values
    full_config = {
        **environment_status["config"], 
        **config,
        # These values are predefined in locustfile
        "duration": 1200,  # 20 minutes, consistent with StagesShapeWithCustomUsers
        "load_dist": "1"   # Medium load
    }
    
    evaluation_status.update({
        "status": "running",
        "current_step": "Starting evaluation",
        "progress": 0,
        "config": full_config,
        "logs": [],
        "results": None
    })
    
    task = asyncio.create_task(run_evaluation_process_safe(full_config))
    task_manager.add_task(task)
    
    return {"message": "Evaluation started"}

async def run_evaluation_process_safe(config: Dict):
    """Safe evaluation process"""
    global evaluation_status
    
    original_stdout = None
    original_stderr = None
    log_file = None
    scaler = None
    task = None
    start_time = datetime.now().isoformat()
    
    try:
        # Use smart logging setup
        original_stdout, original_stderr, log_file = setup_smart_logging("logs/eval_output.log")
        
        log_business_info("Starting evaluation process", "Evaluation")
        log_business_info("Configuration: {}".format(config), "Evaluation")
        
        # Import necessary modules
        from base_module import register_scaler
        from config.exp_config import Config
        from load.load import LoadInjector
        from eval import collect_metrics, SLA_violation, resource_consumption, succ_rate
        
        # Create config object
        eval_config = Config()
        eval_config.select_benchmark = config["benchmark"]
        eval_config.select_scaler = config["scaler"]
        eval_config.locust_exp_name = config["workload"]
        eval_config.locust_exp_time = config["duration"]
        eval_config.locust_load_dist = config["load_dist"]
        
        # Step 1: Register scaler
        evaluation_status["current_step"] = f"Registering {config['scaler']} auto-scaler"
        evaluation_status["progress"] = 10
        log_business_info("Step 1: Registering auto-scaler", "Evaluation")
        
        scaler, task = register_scaler(eval_config)
        log_business_success("Auto-scaler registration completed", "Evaluation")
        
        # Step 2: Inject load
        evaluation_status["current_step"] = f"Injecting {config['workload']} workload"
        evaluation_status["progress"] = 30
        log_business_info("Step 2: Starting workload injection", "Evaluation")
        
        load_injector = LoadInjector(eval_config)
        await load_injector.inject()  # 🔧 Directly use async LoadInjector
        
        log_business_success("Workload injection completed", "Evaluation")
        
        # Step 3: Collect metrics
        evaluation_status["current_step"] = "Collecting performance metrics"
        evaluation_status["progress"] = 80
        log_business_info("Step 3: Collecting performance metrics from Prometheus", "Evaluation")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, collect_metrics, eval_config)
        log_business_success("Metrics collection completed", "Evaluation")
        
        # Step 4: Evaluate results
        evaluation_status["current_step"] = "Calculating results"
        evaluation_status["progress"] = 90
        log_business_info("Step 4: Calculating performance metrics", "Evaluation")
        
        slo_rate = await loop.run_in_executor(None, SLA_violation, eval_config)
        sr = await loop.run_in_executor(None, succ_rate, eval_config)
        cpu, mem = await loop.run_in_executor(None, resource_consumption, eval_config)
        
        log_business_success('SLO violation rate: {:.3f}'.format(slo_rate), "Evaluation")
        log_business_success('Success rate: {:.3f}'.format(sr), "Evaluation")
        log_business_success('CPU usage: {:.3f}, Memory usage: {:.3f} MB'.format(cpu, mem), "Evaluation")
        
        results = {
            "slo_violation_rate": round(float(slo_rate), 3),
            "success_rate": round(float(sr), 3),
            "cpu_usage": round(float(cpu), 3),
            "memory_usage": round(float(mem), 3)
        }
        
        # Step 5: Clean up scaler
        evaluation_status["current_step"] = "Cleaning up auto-scaler"
        evaluation_status["progress"] = 95
        log_business_info("Step 5: Cleaning up auto-scaler", "Evaluation")
        
        if scaler is not None:
            try:
                scaler.cancel()
                log_business_success("Auto-scaler cancelled successfully", "Evaluation")
            except Exception as scaler_error:
                log_business_warning("Scaler cancellation warning: {}".format(str(scaler_error)), "Evaluation")
        
        if task is not None:
            try:
                await task
                log_business_success("Scaler task completed", "Evaluation")
            except Exception as task_error:
                log_business_warning("Scaler task completion warning: {}".format(str(task_error)), "Evaluation")
        
        # Complete
        evaluation_status["status"] = "completed"
        evaluation_status["current_step"] = "Evaluation completed successfully"
        evaluation_status["progress"] = 100
        evaluation_status["results"] = results
        log_business_success("Evaluation completed successfully!", "Evaluation")
        
        # Save test results
        end_time = datetime.now().isoformat()
        # save_test_result_to_history(config, results, start_time, end_time)
        
    except asyncio.CancelledError:
        log_business_warning("Evaluation was cancelled", "Evaluation")
        evaluation_status["status"] = "idle"
        evaluation_status["current_step"] = "Cancelled"
        raise
    except Exception as e:
        log_business_error("Evaluation failed: {}".format(str(e)), "Evaluation")
        import traceback
        traceback.print_exc()
        
        evaluation_status["status"] = "error"
        evaluation_status["current_step"] = f"Evaluation failed: {str(e)}"
        
        # Try emergency cleanup
        try:
            if scaler is not None:
                scaler.cancel()
            if task is not None:
                await task
        except Exception as cleanup_error:
            log_business_error("Emergency cleanup failed: {}".format(str(cleanup_error)), "Evaluation")
        
    finally:
        # Restore output
        if original_stdout and original_stderr and log_file:
            restore_logging(original_stdout, original_stderr, log_file)


# Status query API
@app.get("/api/scaler-eval/environment-status")
def get_environment_status():
    """Get environment preparation status"""
    return environment_status

@app.get("/api/scaler-eval/evaluation-status")
def get_evaluation_status():
    """Get evaluation execution status"""
    return evaluation_status

# Reset environment API
@app.post("/api/scaler-eval/reset-environment")
async def reset_environment():
    """Reset environment state"""
    global environment_status, evaluation_status
    
    try:
        reset_log = {
            "timestamp": datetime.now().isoformat(),
            "message": "Starting environment reset...",
            "level": "info"
        }
        
        environment_status["logs"].append(reset_log)
        
        if evaluation_status["status"] == "running":
            log_business_warning("Stopping running evaluation...", "Reset")
            evaluation_status["status"] = "idle"
            evaluation_status["current_step"] = "Stopped by reset"
            
            stop_log = {
                "timestamp": datetime.now().isoformat(),
                "message": "Evaluation stopped due to environment reset",
                "level": "warning"
            }
            evaluation_status["logs"].append(stop_log)
        
        config_to_clean = None
        
        if evaluation_status.get("config") and evaluation_status["config"].get("benchmark"):
            config_to_clean = evaluation_status["config"]
            log_business_info("Found evaluation config: {}".format(config_to_clean['benchmark']), "Reset")
        elif environment_status.get("config") and environment_status["config"].get("benchmark"):
            config_to_clean = environment_status["config"]
            log_business_info("Found environment config: {}".format(config_to_clean['benchmark']), "Reset")
        
        if config_to_clean:
            try:
                from base_module import end_env
                from config.exp_config import Config
                
                eval_config = Config()
                eval_config.select_benchmark = config_to_clean["benchmark"]
                
                log_business_info("Cleaning environment for benchmark: {}".format(config_to_clean['benchmark']), "Reset")
                
                cleanup_start_log = {
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Starting cleanup for benchmark: {config_to_clean['benchmark']}",
                    "level": "info"
                }
                environment_status["logs"].append(cleanup_start_log)
                
                end_env(eval_config)
                
                log_business_success("Environment cleanup completed", "Reset")
                
                cleanup_done_log = {
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Environment cleanup completed for {config_to_clean['benchmark']}",
                    "level": "info"
                }
                environment_status["logs"].append(cleanup_done_log)
                
            except Exception as cleanup_error:
                log_business_error("Cleanup error: {}".format(str(cleanup_error)), "Reset")
                
                cleanup_error_log = {
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Cleanup error: {str(cleanup_error)}",
                    "level": "error"
                }
                environment_status["logs"].append(cleanup_error_log)
                
                log_business_warning("Continuing with status reset despite cleanup error", "Reset")
        else:
            log_business_info("No active configuration found, skipping cleanup", "Reset")
            
            no_config_log = {
                "timestamp": datetime.now().isoformat(),
                "message": "No active configuration found, skipping cleanup",
                "level": "info"
            }
            environment_status["logs"].append(no_config_log)
        
        reset_logs = environment_status["logs"][-10:] if environment_status["logs"] else []
        
        environment_status = {
            "status": "idle",
            "current_step": "",
            "progress": 0,
            "config": {},
            "logs": reset_logs
        }
        
        evaluation_status = {
            "status": "idle",
            "current_step": "",
            "progress": 0,
            "config": {},
            "logs": [],
            "results": None
        }
        
        final_log = {
            "timestamp": datetime.now().isoformat(),
            "message": "Environment reset completed successfully",
            "level": "info"
        }
        environment_status["logs"].append(final_log)
        
        log_business_success("Environment reset completed successfully", "Reset")
        
        return {"message": "Environment reset successfully"}
        
    except Exception as e:
        log_business_error("Reset failed: {}".format(str(e)), "Reset")
        import traceback
        traceback.print_exc()
        
        try:
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "message": f"Reset failed: {str(e)}",
                "level": "error"
            }
            
            environment_status["status"] = "error"
            environment_status["current_step"] = f"Reset failed: {str(e)}"
            environment_status["logs"].append(error_log)
            
        except:
            environment_status = {
                "status": "error",
                "current_step": f"Reset failed: {str(e)}",
                "progress": 0,
                "config": {},
                "logs": []
            }
        
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

# History record storage path
# HISTORY_FILE = "scaler_eval_history.json"

# def save_test_result_to_history(config: Dict, results: Dict, start_time: str, end_time: str):
#     """
#     Save test results to history
#     """
#     try:
#         # Load existing history
#         history = []
#         if os.path.exists(HISTORY_FILE):
#             with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
#                 history = json.load(f)
        
#         # Create new record
#         record = {
#             "id": f"test-{int(datetime.now().timestamp())}",
#             "benchmark": config["benchmark"],
#             "scaler": config["scaler"],
#             "workload": config["workload"],
#             "duration": config["duration"],
#             "load_dist": config["load_dist"],
#             "start_time": start_time,
#             "end_time": end_time,
#             "results": results,
#             "timestamp": datetime.now().isoformat()
#         }
        
#         # Add to history
#         history.append(record)
        
#         # Limit history count (keep latest 100)
#         if len(history) > 100:
#             history = history[-100:]
        
#         # Save to file
#         with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
#             json.dump(history, f, ensure_ascii=False, indent=2)
        
#         log_business_success("Test result saved to history: {}".format(record['id']), "ScalerEval")
        
#     except Exception as e:
#         log_business_error("Failed to save test result to history: {}".format(str(e)), "ScalerEval")

# Get historical test results
# @app.get("/api/scaler-eval/history")
# def get_test_history():
#     """
#     Get historical test results - based on real history file
#     """
#     try:
#         if os.path.exists(HISTORY_FILE):
#             with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
#                 history = json.load(f)
            
#             # Sort by time in descending order, newest first
#             history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
#             return {"history": history}
#         else:
#             return {"history": []}
            
#     except Exception as e:
#         print(f"Error loading history: {e}")
#         return {"history": []}

# WebSocket endpoints
@app.websocket("/ws/scaler-eval/environment-logs")
async def websocket_environment_logs(websocket: WebSocket):
    await websocket.accept()
    print("Environment logs WebSocket connected")
    task_manager.add_websocket(websocket)
    env_log_reader.add_websocket('environment', websocket)  # 🔧 Use environment log reader
    
    try:
        # Send historical logs
        for log_entry in environment_status["logs"][-50:]:
            try:
                await websocket.send_text(json.dumps(log_entry))
            except Exception as e:
                print(f"Failed to send historical log: {e}")
                break
        
        # Keep connection active
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.ping()
            except Exception as e:
                break
                
    except WebSocketDisconnect:
        print("")
    except Exception as e:
        print(f"")
    finally:
        env_log_reader.remove_websocket('environment', websocket)

@app.websocket("/ws/scaler-eval/evaluation-logs")
async def websocket_evaluation_logs(websocket: WebSocket):
    await websocket.accept()
    print("Evaluation logs WebSocket connected")
    task_manager.add_websocket(websocket)
    eval_log_reader.add_websocket('evaluation', websocket)  # 🔧 Use evaluation log reader
    
    try:
        # Send historical logs
        for log_entry in evaluation_status["logs"][-50:]:
            try:
                await websocket.send_text(json.dumps(log_entry))
            except Exception as e:
                print(f"Failed to send historical log: {e}")
                break
        
        # Keep connection active
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.ping()
            except Exception as e:
                break
                
    except WebSocketDisconnect:
        print("")
    except Exception as e:
        print(f"")
    finally:
        eval_log_reader.remove_websocket('evaluation', websocket)


# Get test status
@app.get("/api/scaler-eval/status")
def get_test_status():
    """
    Get current test status - return comprehensive status
    """
    # If evaluation is running, return evaluation status
    if evaluation_status["status"] != "idle":
        return {
            "status": evaluation_status["status"],
            "current_step": evaluation_status["current_step"],
            "progress": evaluation_status["progress"],
            "config": evaluation_status["config"],
            "logs": evaluation_status["logs"],
            "results": evaluation_status["results"],
            "stage": "evaluation"
        }
    # If environment is preparing, return environment status
    elif environment_status["status"] != "idle":
        return {
            "status": environment_status["status"],
            "current_step": environment_status["current_step"],
            "progress": environment_status["progress"],
            "config": environment_status["config"],
            "logs": environment_status["logs"],
            "results": None,
            "stage": "environment"
        }
    # When both are idle, return idle status
    else:
        return {
            "status": "idle",
            "current_step": "",
            "progress": 0,
            "config": {},
            "logs": [],
            "results": None,
            "stage": "idle"
        }

# Stop test
@app.post("/api/scaler-eval/stop")
async def stop_test():
    """
    Stop current test
    """
    global environment_status, evaluation_status
    
    if environment_status["status"] == "idle" and evaluation_status["status"] == "idle":
        raise HTTPException(status_code=400, detail="No test is currently running")
    
    try:
        # Import your actual modules
        from base_module import end_env
        from config.exp_config import Config
        
        # Use your Config class to create configuration
        eval_config = Config()
        
        # Get configuration from environment status or evaluation status
        config_source = environment_status.get("config") or evaluation_status.get("config")
        if config_source and "benchmark" in config_source:
            eval_config.select_benchmark = config_source["benchmark"]
        
        # Use your end_env function to clean up
        end_env(eval_config)
        
        # Record stop information
        stop_message = {
            "timestamp": datetime.now().isoformat(),
            "message": "Test stopped by user and environment cleaned",
            "level": "info"
        }
        
        # Add to currently active logs
        if evaluation_status["status"] != "idle":
            evaluation_status["logs"].append(stop_message)
        else:
            environment_status["logs"].append(stop_message)
        
        # Reset states
        environment_status["status"] = "idle"
        environment_status["current_step"] = "Stopped by user"
        environment_status["progress"] = 0
        environment_status["config"] = {}
        
        evaluation_status["status"] = "idle"
        evaluation_status["current_step"] = "Stopped by user"
        evaluation_status["progress"] = 0
        evaluation_status["config"] = {}
        evaluation_status["results"] = None
        
        return {"message": "Test stopped and environment cleaned"}
        
    except Exception as e:
        error_message = {
            "timestamp": datetime.now().isoformat(),
            "message": f"Error during stop: {str(e)}",
            "level": "error"
        }
        
        # Add error to logs
        if evaluation_status["status"] != "idle":
            evaluation_status["logs"].append(error_message)
        else:
            environment_status["logs"].append(error_message)
            
        return {"message": f"Test stopped but cleanup may have failed: {str(e)}"}
    

# Manual environment cleanup
@app.post("/api/scaler-eval/cleanup")
async def cleanup_environment(data: Dict = Body(...)):
    """
    Manually clean up test environment
    """
    try:
        # Import your actual modules
        from base_module import end_env
        from config.exp_config import Config
        
        # Use your Config class
        eval_config = Config()
        if "benchmark" in data:
            eval_config.select_benchmark = data["benchmark"]
        
        # Use your end_env function
        end_env(eval_config)
        
        return {"message": "Environment cleaned successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# Check environment status
@app.get("/api/scaler-eval/env-status")
async def check_environment_status():
    """
    Check current environment status
    """
    try:
        # Import your actual modules
        from base_module import init_client
        from config.exp_config import Config
        
        # Use your Config class and init_client function
        config = Config()
        _, kube_client = init_client(config)
        
        # Check namespace status
        namespaces = kube_client.list_namespaces()
        
        benchmark_namespaces = []
        # Use benchmarks configuration from your Config
        for benchmark_name, benchmark_config in config.benchmarks.items():
            namespace = benchmark_config['namespace']
            if namespace in namespaces:
                # Check deployment status in this namespace
                deployments = kube_client.get_deployments(namespace)
                benchmark_namespaces.append({
                    "benchmark": benchmark_name,
                    "namespace": namespace,
                    "status": "active",
                    "deployments": len(deployments),
                    "deployment_list": deployments
                })
        
        return {
            "active_benchmarks": benchmark_namespaces,
            "total_namespaces": len(namespaces),
            "clean": len(benchmark_namespaces) == 0,
            "environment_status": environment_status["status"],
            "evaluation_status": evaluation_status["status"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check environment: {str(e)}")

@app.get("/api/logs/environment")
def get_environment_logs(last_position: int = 0):
    try:
        log_file_path = "logs/pre_output.log"  # 🔧 
        
        if not os.path.exists(log_file_path):
            return {
                "logs": [],
                "current_position": 0,
                "has_more": False
            }
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)
            file_size = f.tell()
            
            if last_position > file_size:
                last_position = 0
            
            f.seek(last_position)
            new_content = f.read()
            current_position = f.tell()
            
            if not new_content:
                return {
                    "logs": [],
                    "current_position": current_position,
                    "has_more": False
                }
            
            lines = new_content.split('\n')
            processed_logs = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                level = determine_log_level(line)
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "message": line,
                    "level": level,
                    "stage": "environment"  
                }
                processed_logs.append(log_entry)
            
            return {
                "logs": processed_logs,
                "current_position": current_position,
                "has_more": current_position < file_size
            }
    
    except Exception as e:
        print(f"Error reading environment logs: {e}")
        return {
            "logs": [],
            "current_position": last_position,
            "has_more": False
        }

@app.get("/api/logs/evaluation")
def get_evaluation_logs(last_position: int = 0):
    try:
        log_file_path = "logs/eval_output.log"  
        
        if not os.path.exists(log_file_path):
            return {
                "logs": [],
                "current_position": 0,
                "has_more": False
            }
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)
            file_size = f.tell()
            
            if last_position > file_size:
                last_position = 0
            
            f.seek(last_position)
            new_content = f.read()
            current_position = f.tell()
            
            if not new_content:
                return {
                    "logs": [],
                    "current_position": current_position,
                    "has_more": False
                }
            
            lines = new_content.split('\n')
            processed_logs = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                level = determine_log_level(line)
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "message": line,
                    "level": level,
                    "stage": "evaluation"  
                }
                processed_logs.append(log_entry)
            
            return {
                "logs": processed_logs,
                "current_position": current_position,
                "has_more": current_position < file_size
            }
    
    except Exception as e:
        print(f"Error reading evaluation logs: {e}")
        return {
            "logs": [],
            "current_position": last_position,
            "has_more": False
        }
    

def determine_log_level(line: str) -> str:
    line_upper = line.upper()
    
    if any(word in line_upper for word in ['ERROR', 'FAILED', 'EXCEPTION', 'TRACEBACK']):
        return "error"
    elif any(word in line_upper for word in ['WARNING', 'WARN']):
        return "warning"
    elif any(word in line_upper for word in ['SUCCESS', 'COMPLETED', 'READY', 'AVALIABLE']):
        return "success"
    else:
        return "info"

@app.post("/api/logs/clear")
def clear_logs():
    """清空日志文件"""
    try:
        log_file_path = "output.log"
        if os.path.exists(log_file_path):
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write("")
        return {"message": "Logs cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)