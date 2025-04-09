import asyncio
from config.exp_config import Config
import os
import subprocess
import time

class LoadInjector():
    def __init__(self, config: Config):
        self.exp_name = config.locust_exp_name
        self.scaler_name = config.select_scaler
        self.benchmark = config.select_benchmark
        self.frontend_url = config.benchmarks[self.benchmark]['entry']
        self.exp_time = config.locust_exp_time
        self.load_dist = config.locust_load_dist
        os.environ['load_dist'] = config.locust_load_dist

    async def inject(self):
        resultPath = f"tmp/{self.benchmark}/dist{self.load_dist}/{self.exp_name}/{self.scaler_name}"
        if not os.path.isdir(resultPath):
            os.makedirs(resultPath)

        locustfile = f'./load/{self.benchmark}/{self.exp_name}_locustfile.py'
        locust_cmd = f'locust -f {locustfile} --host={self.frontend_url} --logfile {resultPath}/log.txt --csv {resultPath}/ --headless'

        # proc = subprocess.Popen(locust_cmd, stdout=subprocess.PIPE, shell=True)
        # proc.wait()
        print('Injecting workloads...')    
        proc = await asyncio.to_thread(subprocess.Popen, locust_cmd, stdout=subprocess.PIPE, shell=True)
        await asyncio.to_thread(proc.wait)
