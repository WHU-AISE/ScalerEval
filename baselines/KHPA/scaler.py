'''
    kubernetes HPA
'''
from baselines.KHPA.cfg import KHPAConfig
from baselines.scaler_template import ScalerTemplate
from utils.exception_uitl import exception_handler
from utils.logger import get_logger

class KHPAScaler(ScalerTemplate):
    def __init__(self, cfg: KHPAConfig, name: str):
        super().__init__(cfg, name)
        self.logger = get_logger('./logs', f'KHPA-{cfg.CPU_threshold}')

    @exception_handler
    async def register(self):
        self.logger.info(f'Register KHPA-{self.cfg.CPU_threshold}...')
        deployments = self.executor.get_deployments_without_state(self.cfg.namespace)
        for idx, deployment in enumerate(deployments):
            self.executor.create_default_HPA(
                namespace=self.cfg.namespace, 
                deployment=deployment, 
                min_replicas=self.cfg.min_count,
                max_replicas=self.cfg.max_count,
                cpu_th=self.cfg.CPU_threshold
            )

    def cancel(self):
        self.logger.info('Remove KHPA...')
        self.executor.remove_default_HPA(self.cfg.namespace)
        
