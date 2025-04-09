'''
    kubernetes HPA
'''
import numpy as np
from simple_pid import PID
import asyncio
import math

from baselines.Showar.cfg import ShowarConfig
from baselines.scaler_template import ScalerTemplate
from utils.logger import get_logger

class ShowarScaler(ScalerTemplate):
    def __init__(self, cfg: ShowarConfig, name: str):
        super().__init__(cfg, name)
        
        self.deployments = self.executor.get_deployments_without_state(self.namespace)

        self.is_running = False
        self.logger = get_logger('./logs', 'Showar')

    async def register(self):
        self.logger.info('Register Showar horizontal scaler...')
        self.is_running = True
        PIDs = {}
        SLOs: dict = self.cfg.SLOs
        self.logger.debug(SLOs)
        for deployment, target in SLOs.items():
            PIDs[deployment] = PID(10, 0, 10, setpoint=target)

        while self.is_running:
            p95_df = self.monitor.get_latency(self.deployments, self.namespace, p=0.95, range=False)
            pod_df = self.monitor.get_pod_num(self.deployments, self.namespace, range=False)
            for deployment, target in SLOs.items():
                try:
                    latency_col = f'{deployment}&0.95'
                    p95 = 0 if latency_col not in p95_df.columns else p95_df[latency_col][0]
                    RM = int(pod_df[f'{deployment}&count'][0])
                    target = SLOs[deployment]
                    controller = PIDs[deployment]
                    min_replicas, max_replicas = self.cfg.min_count, self.cfg.max_count
                    output = -1 * controller(p95)
                    
                    if output > target * (1 + (self.cfg.alpha / 2)):
                        new_RM = math.ceil(RM + max(1, RM * self.cfg.beta))
                    elif output < target * (1 - (self.cfg.alpha / 2)):
                        new_RM = math.ceil(RM - max(1, RM * self.cfg.beta))
                    else:
                        new_RM = RM

                    if (RM != new_RM) and (min_replicas <= new_RM <= max_replicas):
                        self.logger.info(f'{deployment} latency is: {p95}')
                        self.logger.info(f'{deployment} PID score is: {output}')
                        self.logger.info(f'{deployment} is scaled to {new_RM}')
                        self.logger.info('=====================================================')
                        super().scale(deployment, int(new_RM))
                except:
                    self.logger.error(f'encounter some errors in scaling {deployment}...')

            await asyncio.sleep(3)
                    
    def cancel(self):
        self.logger.info('Remove Showar horizontal scaler...')
        self.is_running = False

        
        
