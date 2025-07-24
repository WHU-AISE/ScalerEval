'''
    kubernetes HPA
'''
import asyncio
import sys
import time
import traceback
from threading import Thread

import numpy as np
import math
import schedule
import networkx as nx
import scipy

from baselines.PBScaler.cfg import PBScalerConfig
from baselines.PBScaler.rf_predictor import Predictor
from baselines.scaler_template import ScalerTemplate
from utils.exception_uitl import exception_handler
from utils.logger import get_logger
from utils.io_util import load_pkl


class PBScaler(ScalerTemplate):
    def __init__(self, cfg: PBScalerConfig, name: str):
        super().__init__(cfg, name)

        self.SLA = cfg.SLA
        deployments = self.executor.get_deployments_without_state(self.namespace)
        self.mss = sorted(deployments)
        self.logger = get_logger('./logs', 'PBScaler')
        

    @exception_handler
    async def register(self):
        self.logger.info('Register PBScaler horizontal scaler...')
        self.is_running = True
        schedule.clear()
        schedule.every(self.cfg.ab_check_interval).seconds.do(self.anomaly_detect)
        schedule.every(self.cfg.waste_check_interval).seconds.do(self.waste_detection)
        # schedule.every(self.optimize_all_interval).seconds.do(self.optimize_all_mss)
        self.thread = Thread(target=self.run_schedule)
        self.thread.start()

    def run_schedule(self):
        while self.is_running:
            schedule.run_pending()
        schedule.clear()


    def cancel(self):
        self.logger.info('Remove PBScaler horizontal scaler...')
        self.is_running = False


    @exception_handler
    def get_svc_count(self, svcs):
        cur_time = int(round(time.time()))
        self.monitor.set_time_range(cur_time-60, cur_time, step=5)
        svc_counts_df = self.monitor.get_pod_num(svcs, self.namespace, range=False)
        def modify_column_name(col):
            return col.replace('&count', '')
        svc_counts_df.rename(columns=lambda x: modify_column_name(x), inplace=True)
        svc_counts = svc_counts_df.iloc[0].to_dict()
        return svc_counts

    @exception_handler
    def anomaly_detect(self):
        cur_time = int(round(time.time()))
        self.monitor.set_time_range(cur_time-60, cur_time, step=5)
        latency_df = self.monitor.get_latency(self.mss, self.namespace, p=0.9, range=True)
        for ms in self.mss:
            if f'{ms}&0.9' in latency_df.columns:
                latency = latency_df[f'{ms}&0.9'].values.mean()
                if latency > self.SLA * (1 + self.cfg.alpha / 2):
                    self.root_analysis()
        


    @exception_handler
    def waste_detection(self):
        cur_time = int(round(time.time()))
        self.monitor.set_time_range(cur_time - 60, cur_time, step=5)
        latency_df = self.monitor.get_latency(self.mss, self.namespace, p=0.9, range=True)
        for ms in self.mss:
            if f'{ms}&0.9' in latency_df.columns:
                latency = latency_df[f'{ms}&0.9'].values.mean()
                if latency > self.SLA * (1 + self.cfg.alpha / 2):
                    return
        cur_time = int(round(time.time()))
        self.monitor.set_time_range(cur_time - 60, cur_time, step=5)
        now_qps_df = self.monitor.get_svc_qps(deployments=self.mss, namespace=self.namespace, range=True)

        self.monitor.set_time_range(cur_time - 300, cur_time - 60, step=5)
        old_qps_df = self.monitor.get_svc_qps(deployments=self.mss, namespace=self.namespace, range=True)

        waste_mss = []

        '''Hypothesis µ testing
        a: now_qps µ
        b: old_qps µ0
        H0: µ >= µ0
        H1: µ < µ0
        '''
        for svc in self.mss:
            qps_col = svc +'&qps'
            if qps_col in now_qps_df.columns and qps_col in old_qps_df.columns:
                t, p = scipy.stats.ttest_ind(now_qps_df[qps_col], old_qps_df[qps_col] * self.cfg.beta, equal_var=False)
                if t < 0 and p <= 0.05:
                    waste_mss.append(svc)
        self.logger.info(f'the waste mss are {waste_mss}')
        svc_counts = self.get_svc_count(waste_mss)
        roots = list(filter(lambda ms: svc_counts[ms] > self.cfg.min_count, waste_mss))
        if len(roots) != 0:
            self.choose_action(target_svcs=roots, option='reduce')

    @exception_handler
    def root_analysis(self):
        call_latency = self.monitor.get_call_latency(self.namespace, p=0.9, range=False).iloc[0].to_dict()
        calls = [call for call, latency in call_latency.items() if call != 'timestamp']
        ab_dg, personal_array = self.build_abnormal_subgraph(calls)
        self.logger.debug(f"personal_array: {personal_array}")
        nodes = [node for node in ab_dg.nodes]
        if len(nodes) == 1:
            rank_list = [(nodes[0], 1)]
        else:
            st = time.time()
            rank_list = nx.pagerank(ab_dg, alpha=0.85, personalization=personal_array, max_iter=1000)
            ed = time.time()
            self.logger.debug(f'the time cost of rcl is {(ed-st):.2f}')
            rank_list = sorted(rank_list.items(), key=lambda x: x[1], reverse=True)
        self.logger.info(f"rank list: {rank_list}")
        rank_list = [ms for ms, _ in rank_list]
        svc_counts = self.get_svc_count(rank_list)
        roots = list(filter(lambda root: svc_counts[root] < self.cfg.max_count, rank_list))[:self.cfg.k]
        if len(roots) != 0:
            self.choose_action(target_svcs = roots, option = 'add')

    @exception_handler
    def choose_action(self, target_svcs, option='add'):
        svc_count = self.get_svc_count(self.mss)
        workloads, replicas, mask = [], [], []

        dim = len(target_svcs)
        if option == 'add':
            self.logger.info('begin scale out')
            min_array, max_array = [int(svc_count[t]) + 1 if svc_count[t]+1 < self.cfg.max_count else svc_count[t] for t in target_svcs], [self.cfg.max_count] * dim
        elif option == 'reduce':
            self.logger.info('begin scale in')
            min_array, max_array = [self.cfg.min_count] * dim, [int(svc_count[t]) for t in target_svcs if svc_count[t] > self.cfg.min_count]
            threshold_array = np.array(max_array) - 1
            min_array = np.maximum(min_array, threshold_array)
        elif option == 'none':
            self.logger.info('optimize for all microservices')
            min_array, max_array = [self.cfg.min_count] * dim, [self.cfg.max_count] * dim
        else:
            raise NotImplementedError()
        qps = self.monitor.get_svc_qps(self.mss, self.namespace, range=False)
        for ms in self.mss:
            if ms + '&qps' in qps.keys():
                workloads.append(qps[ms + '&qps'].values[0])
            else:
                workloads.append(0)
            if ms in target_svcs:
                mask.append(1)
            else:
                mask.append(0)
            replicas.append(svc_count[ms])

        '''
        optimizing with genetic algorithms
        only optimize the root services
        '''
        predictor = load_pkl(self.cfg.predictor_path)
        problem = ScalingProblem(
            predictor=predictor, mask=mask, replicas=replicas, workloads=workloads, lowerBounds=min_array, upperBounds=max_array
        )
        algorithm = ea.soea_SGA_templet(
            problem=problem,
            population=ea.Population(Encoding="BG", NIND=50),
            MAXGEN=10,
            logTras=0
        )
        st = time.time()
        res = ea.optimize(
            algorithm,
            verbose=False,
            drawing=0,
            outputMsg=False,
            drawLog=False,
            saveFlag=False,
        )
        ed = time.time()
        vars = res["Vars"].flatten().tolist()
        fitness = res["ObjV"].flatten().tolist()[0]
        self.logger.debug(f'the workloads is {workloads}')
        self.logger.debug(f'the replicas is {replicas}')
        self.logger.debug(f'the mask is {mask}')
        self.logger.debug(f'the vars is {vars}')
        self.logger.debug(f"the fitness of GA is {fitness:.2f}")
        self.logger.debug(f"the time cost of GA is {(ed-st):.2f}")
        actions = {}
        for i in range(len(vars)):
            actions[target_svcs[i]] = vars[i]

        self.execute_task(actions)

    @exception_handler
    def build_abnormal_subgraph(self, calls):
        """
            1. collect metrics for all abnormal services
            2. build the abnormal subgraph with abnormal calls
            3. weight the c by Pearson correlation coefficient
        """
        p=0.9
        ab_sets = set()
        for ab_call in calls:
            ab_sets.update(ab_call.split('_'))
        if 'unknown' in ab_sets: ab_sets.remove('unknown')
        if 'istio-ingressgateway' in ab_sets: ab_sets.remove('istio-ingressgateway')
        ab_mss = list(ab_sets)
        ab_mss.sort()
        end = int(round(time.time()))
        begin= end - 60
        self.monitor.set_time_range(begin, end, step=5)
        ab_metric_df = self.monitor.get_metrics(ab_mss, self.namespace, range=True)
        ab_svc_latency_df = self.monitor.get_latency(ab_mss, self.namespace, p=p, range=True)
        ab_svc_latency_df = ab_svc_latency_df[[col for col in ab_svc_latency_df.columns if col.split('&')[0] in ab_mss]]

        ab_dg = nx.DiGraph()
        ab_dg.add_nodes_from(ab_mss)
        edges = []
        for ab_call in calls:
            edge = ab_call.split('_')
            if 'unknown' in edge or 'istio-ingressgateway' in edge:
                continue
            metric_df = ab_metric_df[[col for col in ab_metric_df.columns if col.startswith(edge[1])]]
            try:
                edges.append((edge[0], edge[1], self.cal_weight(ab_svc_latency_df[edge[0]+f'&{p}'], metric_df)))
            except:
                edges.append((edge[0], edge[1], 0))
        ab_dg.add_weighted_edges_from(edges)

        # calculate topology potential
        anomaly_score_map = {}
        for node in ab_mss:
            try:
                e_latency_array = ab_svc_latency_df[node+f'&{p}']
                ef = e_latency_array[e_latency_array > self.SLA].count()
                anomaly_score_map[node] = ef
            except:
                anomaly_score_map[node] = 0
        personal_array = self.cal_topology_potential(ab_dg, anomaly_score_map)

        return ab_dg, personal_array

    @exception_handler
    def cal_weight(self, latency_array, metric_df):
        max_corr = 0
        for col in metric_df.columns:
            temp = abs(metric_df[col].corr(latency_array))
            if temp > max_corr:
                max_corr = temp
        return max_corr

    @exception_handler
    def cal_topology_potential(self, ab_DG, anomaly_score_map: dict):
        personal_array = {}
        for node in ab_DG.nodes:
            # calculate topological potential
            sigma = 1
            potential = anomaly_score_map[node]
            pre_nodes = ab_DG.predecessors(node)
            for pre_node in pre_nodes:
                potential += (anomaly_score_map[pre_node] * math.exp(-1 * math.pow(1 / sigma, 2)))
                for pre2_node in ab_DG.predecessors(pre_node):
                    if pre2_node != node:
                        potential += (anomaly_score_map[pre2_node] * math.exp(-1 * math.pow(2 / sigma, 2)))
            personal_array[node] = potential
        return personal_array

    @exception_handler
    def execute_task(self, actions):
        for ms, replica_num in actions.items():
            super().scale(ms, int(replica_num))
            self.logger.info('scale {} to {}'.format(ms, int(actions[ms])))

    @exception_handler
    def optimize_all_mss(self):
        self.choose_action(self.mss, option='none')



import geatpy as ea
np.set_printoptions(suppress=True)

class ScalingProblem(ea.Problem):
    def __init__(self,
                 predictor: Predictor,
                 mask,
                 replicas,
                 workloads,
                 lowerBounds,
                 upperBounds):
        name = 'ScalingProblem'
        self.predictor = predictor
        self.mask = np.array(mask)
        self.replicas = np.array(replicas)
        self.workloads = np.array(workloads)
        self.total_max_num = np.sum(upperBounds)
        M = 1  # number of objective
        maxormins = [-1]  # -1: maximize; 1: minimize
        Dim = len(lowerBounds)
        varTypes = [1] * Dim # 0: continuous; 1: discrete
        lbin = [1] * Dim  # 1: include lower bound
        ubin = [1] * Dim  # 1: include upper bound
        ea.Problem.__init__(self,
                            name,
                            M,
                            maxormins,
                            Dim,
                            varTypes,
                            lowerBounds,
                            upperBounds,
                            lbin,
                            ubin)


    def evalVars(self, Vars):
        # fill the mask
        expanded_replicas = np.tile(self.replicas, (Vars.shape[0], 1))
        expanded_workloads = np.tile(self.workloads, (Vars.shape[0], 1))
        expanded_mask = np.tile(self.mask, (Vars.shape[0], 1))
        new_values_matrix = np.zeros_like(expanded_replicas)
        new_values_matrix[expanded_mask == 1] = Vars.flatten()
        final_svc_count = np.where(expanded_mask == 1, new_values_matrix, expanded_replicas)
        final_input = np.hstack([final_svc_count, expanded_workloads])

        R1 = 1-self.predictor.predict(final_input)
        R2 = (1 - (Vars.sum(axis=1) / self.total_max_num))
        alpha, beta = 0.5, 0.5
        return (alpha * R1 + beta * R2).reshape(-1,1)