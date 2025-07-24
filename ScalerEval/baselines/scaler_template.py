from baselines.scaler_config_template import ScalerConfig
from utils.cloud.executor import KubernetesClient
from utils.cloud.monitor import PrometheusClient


class ScalerTemplate:
    def __init__(self, cfg: ScalerConfig, name):
        self.name = name
        self.cfg = cfg
        self.namespace = cfg.namespace
        self.monitor = PrometheusClient(cfg.monitor_url)
        self.executor = KubernetesClient(cfg.excutor_cfg)

    async def register(self):
        # register the scaler
        pass

    def cancel(self):
        # remove the scaler
        pass

    def scale(self, ms, replica_num):
        # scaling the replcas of a microservice to the expected count
        self.executor.patch_scale(ms, int(replica_num), self.namespace, async_req=True)
