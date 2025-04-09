from config.exp_config import Config


class ScalerConfig:
    def __init__(self, config: Config):
        self.monitor_url = config.prom_url
        self.excutor_cfg = config.kube_config
        self.scaler_name = config.select_scaler
        self.namespace = config.benchmarks[config.select_benchmark]['namespace']
        self.min_count = 1
        self.max_count = 8

        self.SLA = config.benchmarks[config.select_benchmark]['SLA']