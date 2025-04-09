from baselines.scaler_config_template import ScalerConfig


class ShowarConfig(ScalerConfig):
    def __init__(self, config):
        super().__init__(config)

        self.SLOs = {}
        if config.select_benchmark == 'hipster':
            self.SLOs = {'adservice': 10, 'cartservice': 100, 'checkoutservice': 100, 'currencyservice': 10,
                        'emailservice': 10, 'frontend': self.SLA, 'paymentservice': 10, 'productcatalogservice':10,
                        'recommendationservice': 50, 'shippingservice':10}
            
        elif config.select_benchmark == 'sockshop':
            self.SLOs = {'front-end': self.SLA, 'carts': 100, 'orders': self.SLA, 'shipping': 100, 'catalogue': 10,
                        'payment': 10, 'queue-master': 10, 'user': 10}
        
        self.alpha = 0.1
        self.beta = 1