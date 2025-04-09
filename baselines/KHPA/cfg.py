from baselines.scaler_config_template import ScalerConfig


class KHPAConfig(ScalerConfig):
    def __init__(self, config):
        super().__init__(config)
        self.CPU_threshold = 80

    def set_cpu_threshold(self, threshold):
        self.CPU_threshold = threshold