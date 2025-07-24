# import asyncio
# from config.exp_config import Config
# import os
# import subprocess
# import time

# class LoadInjector():
#     def __init__(self, config: Config):
#         self.exp_name = config.locust_exp_name
#         self.scaler_name = config.select_scaler
#         self.benchmark = config.select_benchmark
#         self.frontend_url = config.benchmarks[self.benchmark]['entry']
#         self.exp_time = config.locust_exp_time
#         self.load_dist = config.locust_load_dist
#         os.environ['load_dist'] = config.locust_load_dist

#     async def inject(self):
#         resultPath = f"tmp/{self.benchmark}/dist{self.load_dist}/{self.exp_name}/{self.scaler_name}"
#         if not os.path.isdir(resultPath):
#             os.makedirs(resultPath)

#         locustfile = f'./load/{self.benchmark}/{self.exp_name}_locustfile.py'
#         locust_cmd = f'locust -f {locustfile} --host={self.frontend_url} --logfile {resultPath}/log.txt --csv {resultPath}/ --headless'

#         # proc = subprocess.Popen(locust_cmd, stdout=subprocess.PIPE, shell=True)
#         # proc.wait()
#         print('Injecting workloads...')    
#         proc = await asyncio.to_thread(subprocess.Popen, locust_cmd, stdout=subprocess.PIPE, shell=True)
#         await asyncio.to_thread(proc.wait)





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
        
        # 构建Locust命令
        locust_cmd = [
            'locust',
            '-f', locustfile,
            '--host', self.frontend_url,
            '--logfile', f'{resultPath}/log.txt',
            '--csv', f'{resultPath}/',
            '--headless'
        ]

        print('[LoadInjector] Injecting workloads...')
        print(f'[LoadInjector] Command: {" ".join(locust_cmd)}')
        
        try:
            # 🔧 使用线程池执行，避免Windows异步subprocess问题
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_locust_sync, locust_cmd, resultPath)
            
        except Exception as e:
            print(f'[LoadInjector] Error during workload injection: {str(e)}')
            raise
        
        print('[LoadInjector] Load injection process finished')

    def _run_locust_sync(self, locust_cmd, result_path):
        """同步执行Locust命令的辅助方法"""
        try:
            process = subprocess.Popen(
                locust_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=os.environ.copy()
            )
            
            line_count = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output.strip():
                    line_count += 1
                    print(f"[Locust] {output.strip()}")
                    
                    if line_count % 10 == 0:
                        print(f"[LoadInjector] Processed {line_count} log lines...")
            
            return_code = process.poll()
            
            if return_code == 0:
                print('[LoadInjector] Workload injection completed successfully')
            else:
                print(f'[LoadInjector] Workload injection finished with return code: {return_code}')
            
            self._check_generated_files(result_path)
            
        except Exception as e:
            print(f'[LoadInjector] Error in sync execution: {str(e)}')
            raise

    def _check_generated_files(self, result_path):
        """检查Locust生成的结果文件（保持不变）"""
        try:
            expected_files = [
                '_stats.csv',
                '_stats_history.csv', 
                '_failures.csv',
                'log.txt'
            ]
            
            print(f'[LoadInjector] Checking generated files in {result_path}...')
            
            for file_name in expected_files:
                file_path = os.path.join(result_path, file_name)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f'[LoadInjector] ✓ {file_name} generated successfully ({file_size} bytes)')
                else:
                    print(f'[LoadInjector] ✗ {file_name} not found')
            
            if os.path.exists(result_path):
                all_files = os.listdir(result_path)
                print(f'[LoadInjector] All files in result directory: {all_files}')
                
        except Exception as e:
            print(f'[LoadInjector] Error checking generated files: {str(e)}')