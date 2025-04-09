
import time
import os
import asyncio
from base_module import end_env, init_env, register_scaler
from config.exp_config import Config
from load.load import LoadInjector
from eval import collect_metrics, SLA_violation, resource_consumption, succ_rate



async def performance_comparison_flow():
    config = Config()
    config.locust_exp_name = 'wiki'
    for benchmark in ['hipster', 'sockshop']:
        for scaler in ['None', 'KHPA-20', 'KHPA-50', 'KHPA-80', 'Showar', 'PBScaler']:
            config.select_benchmark = benchmark
            config.select_scaler = scaler

            # init microservices
            init_env(config)

            # register autoscaler
            scaler, task = register_scaler(config)

            # inject workload
            load_injector = LoadInjector(config)
            await load_injector.inject()

            # collect metrics
            collect_metrics(config)

            # cancel autoscaler
            scaler.cancel()
            if task != None:
                await task

            # stop microservices
            end_env(config)
            time.sleep(60)

def eval():
    config = Config()
    for scaler in ['None','KHPA-20', 'KHPA-50', 'KHPA-80', 'Showar', 'PBScaler']:
        config.select_scaler = scaler
        print(f'evaluate {scaler}')
        slo_rate = SLA_violation(config)
        print(f'SLO violation rate: {slo_rate:.3f}')
        sr = succ_rate(config)
        print(f'success rate: {sr:.3f}')
        cpu, mem = resource_consumption(config)
        print(f'CPU usage: {cpu:.3f} cores, Memory usage: {mem:.3f} MB')
        print('*' *100)


def clear_environment():
    config = Config()
    end_env(config)


async def main():
    await performance_comparison_flow()
        

if __name__ == '__main__':
    asyncio.run(main())
    # eval()
    # clear_environment()