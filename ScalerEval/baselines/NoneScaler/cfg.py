from baselines.scaler_config_template import ScalerConfig


class NoneConfig(ScalerConfig):
    def __init__(self, config):
        super().__init__(config)