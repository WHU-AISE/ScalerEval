
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math

SVCS = {
    'hipster': ['adservice','cartservice','checkoutservice','currencyservice','emailservice','frontend','paymentservice','productcatalogservice','recommendationservice','shippingservice'],

    'sockshop': ['carts', 'carts-db', 'catalogue', 'catalogue-db', 'front-end', 'orders', 'orders-db', 'payment', 'queue-master', 'rabbitmq', 'session-db', 'shipping', 'user', 'user-db']
}

def load_data(dir):
    record = pd.read_csv(f'{dir}/record.csv')
    locust_stats = pd.read_csv(f'{dir}/_stats_history.csv')
    return record, locust_stats


def system_throughput_analysis(save_dir: str,
                        record: pd.DataFrame, 
                        locust_stats: pd.DataFrame):
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(16, 4))
    ax0, ax1 = axes[0], axes[1]
    # plot user count
    locust_stats['User Count'].plot(ax=ax0, kind='line', title='User Count')
    ax0.set_ylabel('# of users')
    ax0.set_xlabel('Time (s)')
    # plot throughput of locust_states, istio-ingressgateway
    locust_stats['Requests/s'].plot(ax=ax1, kind='line')
    locust_stats['Failures/s'].plot(ax=ax1, kind='line')
    record['istio-ingressgateway&qps'].plot(ax=ax1, kind='line', title='Throughput')
    ax1.set_ylabel('Transac. per Sec (TPS)')
    ax1.set_xlabel('Time (s)')
    fig.legend(loc='upper center', prop={'size': 12}, ncol=4)
    fig.savefig(f'{save_dir}/system-throughput.png', format='png', bbox_inches='tight')
    plt.close(fig)

def e2e_latency_analysis(save_dir: str,
                        record: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 6))
    record['istio-ingressgateway&0.5'].plot(ax=ax, label='P50')
    record['istio-ingressgateway&0.9'].plot(ax=ax, label='P90')
    record['istio-ingressgateway&0.95'].plot(ax=ax, label='P95')
    record['istio-ingressgateway&0.99'].plot(ax=ax, label='P99')
    # ax.set_ylim(0, 1000)
    ax.set_title('E2e tail latency (ms)')
    ax.set_xlabel('Time (s)')
    plt.legend(loc='upper center', prop={'size': 12}, ncol=4)
    plt.savefig(f'{save_dir}/e2e-latency.png', format='png', bbox_inches='tight')
    plt.close()

def pod_throughput_metric_analysis(save_dir: str,
                            record: pd.DataFrame):
    '''
        plot the correlation of pod-level throughput with metric
    '''
    qps_cols = [col for col in record.columns if col.endswith('qps')]
    svcs = []
    for qps_col in qps_cols:
        if 'istio-ingressgateway' not in qps_col:
            svc = qps_col.replace('&qps', '')
            svcs.append(svc)
            replica_col = qps_col.replace('&qps', '&count')
            record[f'{svc}&qps_per_pod'] = record[qps_col] / record[replica_col]

    svc_num = len(svcs)
    for metric in ['cpu', 'mem']:
        col_num = 3
        row_num = math.ceil(svc_num/col_num)
        fig, axes = plt.subplots(nrows=row_num, ncols=col_num, figsize=(col_num*5, row_num * 3))
        axes = axes.flatten()
        handlers, labels = [], []
        for idx, svc in enumerate(svcs):
            metric_col = f'{svc}&{metric}_usage_mean'
            ax = axes[idx]
            ax.set_title(f'{svc}')
            record[f'{svc}&qps_per_pod'].plot(ax=ax, kind='line', label='Throughput per pod', color='blue')
            handler1 = ax.lines[-1]
            ax.set_ylabel('Transac. per Sec (TPS)')
            ax.set_xlabel('Time (s)')

            tmp_ax = ax.twinx()
            (record[metric_col]/record[f'{svc}&{metric}_limit']).plot(ax=tmp_ax, kind='line', label=f'{metric} usage per pod', color='green')
            handler2 = tmp_ax.lines[-1]
            tmp_ax.set_ylabel(f'{metric} (%)')
            tmp_ax.set_xlabel('Time (s)')
            tmp_ax.set_ylim(0, 1)

            handlers.append(handler1)
            handlers.append(handler2)
            labels.append(handler1.get_label())
            labels.append(handler2.get_label())
        
        unique_labels = list(dict.fromkeys(labels))
        unique_handlers = [handlers[labels.index(label)] for label in unique_labels]
        
        fig.legend(unique_handlers, unique_labels, loc='upper center', prop={'size': 12}, ncol=4)
        fig.subplots_adjust(wspace=0.5, hspace=0.5)
        fig.savefig(f'{save_dir}/throughput-{metric}.png', format='png', bbox_inches='tight')
        plt.close(fig)


def latency_metric_analysis(save_dir: str,
                            record: pd.DataFrame):
    '''
        plot the correlation of pod-level throughput with metric
    '''
    svcs = [col.split('&')[0] for col in record.columns if col.endswith('0.5') and 'istio-ingressgateway' not in col]

    svc_num = len(svcs)
    col_num = 3
    row_num = math.ceil(svc_num/col_num)
    for latency, latency_name in list(zip(
        ['0.5', '0.9', '0.95', '0.99'],
        ['P50', 'P90', 'P95', 'P99']
    )):
        for metric in ['cpu', 'mem']:
            col_num = 3
            row_num = math.ceil(svc_num/col_num)
            fig, axes = plt.subplots(nrows=row_num, ncols=col_num, figsize=(col_num*5, row_num * 3))
            axes = axes.flatten()
            handlers, labels = [], []
            for idx, svc in enumerate(svcs):
                ax = axes[idx]
                ax.set_title(f'{svc}')
                record[f'{svc}&{latency}'].plot(ax=ax, kind='line', label=f'{latency_name}', color='blue')
                handler1 = ax.lines[-1]
                ax.set_ylabel('Latency (ms)')
                ax.set_xlabel('Time (s)')

                tmp_ax = ax.twinx()
                metric_col = f'{svc}&{metric}_usage_mean'
                (record[metric_col]/record[f'{svc}&{metric}_limit']).plot(ax=tmp_ax, kind='line', label=f'{metric} usage per pod', color='green')
                handler2 = tmp_ax.lines[-1]
                tmp_ax.set_ylabel(f'{metric} (%)')
                tmp_ax.set_xlabel('Time (s)')
                tmp_ax.set_ylim(0, 1)

                handlers.append(handler1)
                handlers.append(handler2)
                labels.append(handler1.get_label())
                labels.append(handler2.get_label())
        
            unique_labels = list(dict.fromkeys(labels))
            unique_handlers = [handlers[labels.index(label)] for label in unique_labels]
            
            fig.legend(unique_handlers, unique_labels, loc='upper center', prop={'size': 12}, ncol=4)
            fig.subplots_adjust(wspace=0.5, hspace=0.5)
            fig.savefig(f'{save_dir}/{latency_name}-{metric}.png', format='png', bbox_inches='tight')
            plt.close(fig)

def pod_throughput_latency_analysis(save_dir: str,
                record: pd.DataFrame):
    '''
        plot the correlation of pod-level throughput with metric
    '''
    qps_cols = [col for col in record.columns if col.endswith('qps')]
    svcs = []
    for qps_col in qps_cols:
        if 'istio-ingressgateway' not in qps_col:
            svc = qps_col.replace('&qps', '')
            svcs.append(svc)
            replica_col = qps_col.replace('&qps', '&count')
            record[f'{svc}&qps_per_pod'] = record[qps_col] / record[replica_col]

    svc_num = len(svcs)
    col_num = 3
    row_num = math.ceil(svc_num/col_num)
    for metric, metric_name in list(zip(
        ['0.5', '0.9', '0.95', '0.99'],
        ['P50', 'P90', 'P95', 'P99']
    )):
        handlers, labels = [], []
        fig, axes = plt.subplots(nrows=row_num, ncols=col_num, figsize=(col_num*5, row_num * 3))
        axes = axes.flatten()
        for idx, svc in enumerate(svcs):
            ax = axes[idx]
            ax.set_title(f'{svc}')
            record[f'{svc}&qps_per_pod'].plot(ax=ax, kind='line', label='Throughput per pod', color='blue')
            handler1 = ax.lines[-1]
            ax.set_ylabel('Transac. per Sec (TPS)')
            ax.set_xlabel('Time (s)')

            tmp_ax = ax.twinx()
            record[f'{svc}&{metric}'].plot(ax=tmp_ax, kind='line', label=f'{metric_name}', color='red')
            handler2 = tmp_ax.lines[-1]
            tmp_ax.set_ylabel(f'Latency (ms)')
            tmp_ax.set_xlabel('Time (s)')

            handlers.append(handler1)
            handlers.append(handler2)
            labels.append(handler1.get_label())
            labels.append(handler2.get_label())
        unique_labels = list(dict.fromkeys(labels))
        unique_handlers = [handlers[labels.index(label)] for label in unique_labels]
        
        fig.legend(unique_handlers, unique_labels, loc='upper center', prop={'size': 12}, ncol=4)
        fig.subplots_adjust(wspace=0.5, hspace=0.5)
        fig.savefig(f'{save_dir}/throughput-{metric_name}.png', format='png', bbox_inches='tight')
        plt.close(fig)


def cpu_mem_hot(save_dir: str,
                record: pd.DataFrame):
    cpu_limit_cols = [col for col in record.columns if col.endswith('cpu_limit')]
    mem_limit_cols = [col for col in record.columns if col.endswith('mem_limit')]

    cpu_dic = {}
    win_size=30 # 30 seconds window
    for cpu_limit_col in cpu_limit_cols:
        svc = cpu_limit_col.replace('&cpu_limit', '')
        cpu_usage_col = cpu_limit_col.replace('&cpu_limit', '&cpu_usage_mean')
        tmp_cpu_rate = record[cpu_usage_col]/record[cpu_limit_col]
        avg_cpus = []
        for i in range(0, len(tmp_cpu_rate), win_size):
            avg_cpu = np.mean(tmp_cpu_rate[i:i+win_size])
            avg_cpus.append(avg_cpu)
        cpu_dic[svc] = avg_cpus

    mem_dic = {}
    for mem_limit_col in mem_limit_cols:
        svc = mem_limit_col.replace('&mem_limit', '')
        mem_usage_col = mem_limit_col.replace('&mem_limit', '&mem_usage_mean')
        tmp_mem_rate = record[mem_usage_col]/record[mem_limit_col]
        avg_mems = []
        for i in range(0, len(tmp_mem_rate), win_size):
            avg_mem = np.mean(tmp_mem_rate[i:i+win_size])
            avg_mems.append(avg_mem)
        mem_dic[svc] = avg_mems
    
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(20, 5))
    axes = axes.flatten()
    cpu_data=np.array(list(cpu_dic.values()))
    mem_data=np.array(list(mem_dic.values()))

    for idx, (dic, data, y_label) in enumerate(list(zip(
        [cpu_dic, mem_dic],
        [cpu_data, mem_data],
        ['CPU rate (%)', 'Memory rate (%)']
    ))):
        ax = axes[idx]
        cax = ax.imshow(data, cmap='Reds', origin='upper', aspect="auto", vmin=0, vmax=1)
        ax.set_xticks(range(data.shape[1]))
        # print(data.shape)
        ax.set_xticklabels(np.linspace(0, data.shape[1], num=data.shape[1], endpoint=False, dtype=int))
        ax.set_yticks(range(data.shape[0]))
        ax.set_yticklabels(list(dic.keys()))
        cbar = fig.colorbar(cax)
        cbar.set_label(y_label)
    fig.subplots_adjust(wspace=0.5, hspace=0.5)
    fig.savefig(f'{save_dir}/cpu-mem-hot.png', format='png', bbox_inches='tight')
    plt.close(fig)




if __name__ == '__main__':
    benchmarks = ['hipster', 'sockshop']
    scalers = ['None', 'KHPA-20', 'KHPA-50','KHPA-80','Showar', 'PBScaler']
    dists = ['dist1']
    exps = ['wiki']

    for benchmark in benchmarks:
        for scaler in scalers:
            for dist in dists:
                for exp in exps:
                    dir = f'./tmp/{benchmark}/{dist}/{exp}/{scaler}/'
                    if os.path.exists(dir):
                        save_dir = f'./analysis/res/{benchmark}/{dist}/{exp}/{scaler}/'
                        if not os.path.isdir(save_dir):
                            os.makedirs(save_dir)
                        record, locust_stats = load_data(dir)
                        e2e_latency_analysis(save_dir, record)
                        system_throughput_analysis(save_dir, record, locust_stats)
                        pod_throughput_metric_analysis(save_dir, record)
                        pod_throughput_latency_analysis(save_dir, record)
                        latency_metric_analysis(save_dir, record)
                        cpu_mem_hot(save_dir, record)
                        
                        

