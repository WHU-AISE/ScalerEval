from baselines.scaler_config_template import ScalerConfig


class PBScalerConfig(ScalerConfig):
    def __init__(self, config):
        super().__init__(config)

        self.ab_check_interval = 10
        self.waste_check_interval = 60
        self.optimize_all_interval = 240
        self.alpha = 0
        self.beta = 0.9
        self.k = 4 if self.namespace == 'online-boutique' else 2
        self.predictor_path = f'baselines/PBScaler/{self.namespace}.pkl'