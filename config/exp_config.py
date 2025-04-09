class Config:
    def __init__(self):
        self.select_benchmark = 'hipster'
        self.select_scaler = 'KHPA-80' # [None, KHPA-20, KHPA-50, KHPA-80, Showar, PBScaler]
        self.locust_exp_name = 'wiki'
        self.locust_exp_time = 1200
        self.locust_load_dist = '1'

        # Prometheus config
        self.prom_url=f'http://192.168.31.68:30001'

        # Kubernetes config
        self.kube_config = './config/kube.yaml'

        # benchmark config
        self.benchmarks = {
            'hipster': {
                'entry': 'http://192.168.31.68:32536', # check the port of istio-ingress-gateway
                'deploy_path': './benchmarks/hipster/hipster.yaml',
                'istio_yaml': './benchmarks/hipster/istio-manifests.yaml',
                'namespace': 'hipster',
                'SLA': 500
            },
            'sockshop': {
                'entry': 'http://192.168.31.68:32536', # check the port of istio-ingress-gateway
                'deploy_path': './benchmarks/sockshop/sockshop.yaml',
                'istio_yaml': './benchmarks/sockshop/istio-manifests.yaml',
                'namespace': 'sockshop',
                'SLA': 500
            }
        }