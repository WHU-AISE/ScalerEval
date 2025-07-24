<template>
    <div class="service-detail">
        <el-card class="box-card">
            <!-- Basic Information -->
            <div class="header">
                <h2>{{ serviceInfo.pod_name }} ({{ serviceInfo.namespace }})</h2>
                <el-tag :type="serviceInfo.status === 'Running' ? 'success' : 'danger'">
                    {{ serviceInfo.status || 'Unknown' }}
                </el-tag>
            </div>

            <!-- Metadata -->
            <el-row :gutter="20" class="meta-row">
                <el-col :span="6">
                    <div class="meta-item">
                        <label>Creation Time</label>
                        <div>{{ serviceInfo.creation_time || 'Unknown' }}</div>
                    </div>
                </el-col>
                <el-col :span="6">
                    <div class="meta-item">
                        <label>Node</label>
                        <div>{{ serviceInfo.node_name || 'Unknown' }}</div>
                    </div>
                </el-col>
                <el-col :span="6">
                    <div class="meta-item">
                        <label>Node IP</label>
                        <div>{{ serviceInfo.node_ip || 'Unknown' }}</div>
                    </div>
                </el-col>
                <el-col :span="6">
                    <div class="meta-item">
                        <label>Pod IP</label>
                        <div>{{ serviceInfo.pod_ip || 'Unknown' }}</div>
                    </div>
                </el-col>
            </el-row>

            <el-tabs v-model="activeTab">
                <el-tab-pane label="Resources" name="resource">
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <div class="chart-container">
                                <h3>CPU Usage (%)</h3>
                                <div ref="cpuChart" style="height: 300px;"></div>
                            </div>
                        </el-col>
                        <el-col :span="12">
                            <div class="chart-container">
                                <h3>Memory Usage (MB)</h3>
                                <div ref="memoryChart" style="height: 300px;"></div>
                            </div>
                        </el-col>
                    </el-row>
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <div class="chart-container">
                                <h3>Network Traffic (KB/s)</h3>
                                <div ref="networkChart" style="height: 300px;"></div>
                            </div>
                        </el-col>
                        <el-col :span="12">
                            <div class="chart-container">
                                <h3>Request Latency (ms)</h3>
                                <div ref="latencyChart" style="height: 300px;"></div>
                            </div>
                        </el-col>
                    </el-row>
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <div class="chart-container">
                                <h3>QPS (Queries Per Second)</h3>
                                <div ref="qpsChart" style="height: 300px;"></div>
                            </div>
                        </el-col>
                        <el-col :span="12">
                            <div class="chart-container">
                                <h3>Filesystem Activity</h3>
                                <div ref="fsChart" style="height: 300px;"></div>
                            </div>
                        </el-col>
                    </el-row>
                </el-tab-pane>

                <el-tab-pane label="Logs" name="logs">
                    <div class="logs-header">
                        <h3>Pod Logs View</h3>
                        <div class="logs-actions">
                            <el-form size="small" inline>
                                <el-form-item label="Container">
                                    <el-select v-model="selectedContainer" placeholder="Select Container" @change="refreshLogs">
                                        <el-option
                                            v-for="container in podContainers"
                                            :key="container"
                                            :label="container"
                                            :value="container"
                                        ></el-option>
                                    </el-select>
                                </el-form-item>
                                <el-form-item label="Log Lines">
                                    <el-input-number v-model="logLines" :min="10" :max="5000" :step="10"></el-input-number>
                                </el-form-item>
                                <el-form-item>
                                    <el-button type="primary" size="small" @click="refreshLogs">
                                        <i class="el-icon-refresh"></i> Refresh
                                    </el-button>
                                    <el-button type="success" size="small" @click="downloadLogs" :disabled="!podLogs">
                                        <i class="el-icon-download"></i> Download
                                    </el-button>
                                </el-form-item>
                            </el-form>
                        </div>
                    </div>

                    <div v-if="logsLoading" class="loading-container">
                        <el-skeleton :rows="10" animated />
                    </div>
                    <div v-else-if="logsError" class="error-container">
                        <el-alert title="Failed to retrieve logs" type="error" :description="logsError" show-icon>
                        </el-alert>
                    </div>
                    <div v-else-if="!podLogs" class="empty-logs">
                        <el-empty description="No log data available"></el-empty>
                    </div>
                    <div v-else>
                        <pre class="log-content">{{ podLogs }}</pre>
                    </div>
                </el-tab-pane>

                <el-tab-pane label="YAML" name="yaml">
                    <div class="yaml-container">
                        <div class="yaml-actions">
                            <el-button type="primary" size="small" @click="fetchPodYaml">
                                <i class="el-icon-refresh"></i> Fetch YAML
                            </el-button>
                            <el-button type="success" size="small" @click="copyYaml" :disabled="!podYaml">
                                <i class="el-icon-document-copy"></i> Copy YAML
                            </el-button>
                        </div>
                        <div v-loading="yamlLoading">
                            <pre v-if="podYaml" class="yaml-content">{{ podYaml }}</pre>
                            <el-empty v-else description="No YAML data available, click the button above to fetch YAML"></el-empty>
                        </div>
                    </div>
                </el-tab-pane>
            </el-tabs>

            <el-button @click="goBack">Back</el-button>
        </el-card>
    </div>
</template>

<script>
import * as echarts from 'echarts';

export default {
    props: ["namespace", "serviceName"], // serviceName is actually the Pod name
    data() {
        return {
            serviceInfo: {
                pod_name: "",
                namespace: "",
                creation_time: "",
                node_name: "",
                node_ip: "",
                pod_ip: "",
                status: "",
                resourceMetrics: {
                    cpu: [],
                    memory: [],
                    timestamps: [],
                    netReceive: [],
                    netTransmit: [],
                    destP50: [],
                    destP90: [],
                    destQps: [],
                    srcQps: [],
                    fsUsage: [],
                    fsWrite: [],
                    fsRead: []
                }
            },
            activeTab: "resource",
            podLogs: "",
            logsLoading: false,
            logsError: null,
            podContainers: ["default"],
            selectedContainer: "default",
            logLines: 100,
            cpuChart: null,
            memoryChart: null,
            networkChart: null,
            latencyChart: null,
            qpsChart: null,
            fsChart: null,
            
            // YAML related
            podYaml: "",
            yamlLoading: false
        };
    },
    watch: {
        activeTab(newVal) {
            // Automatically load logs when switching to logs tab
            if (newVal === 'logs' && !this.podLogs && !this.logsLoading) {
                this.fetchPodLogs();
            }
            // Automatically load YAML when switching to YAML tab
            else if (newVal === 'yaml' && !this.podYaml && !this.yamlLoading) {
                this.fetchPodYaml();
            }
        }
    },
    methods: {
        async fetchMetrics() {
            try {
                const response = await this.$http2.get(`/api/all_metrics/${this.namespace}/${this.serviceName}`);

                // Extract timestamps and metric values
                const timestamps = response.data.timestamps;
                const metrics = response.data.metrics;

                // CPU usage
                this.serviceInfo.resourceMetrics.cpu = metrics.cpu_usage || [];
                // Memory usage
                this.serviceInfo.resourceMetrics.memory = metrics.mem_usage || [];
                // Save timestamps
                this.serviceInfo.resourceMetrics.timestamps = timestamps;

                // Add network metrics
                this.serviceInfo.resourceMetrics.netReceive = metrics.net_receive || [];
                this.serviceInfo.resourceMetrics.netTransmit = metrics.net_trainsmit || [];

                // Add latency metrics
                this.serviceInfo.resourceMetrics.destP50 = metrics.destP50 || [];
                this.serviceInfo.resourceMetrics.destP90 = metrics.destP90 || [];

                // Add QPS metrics
                this.serviceInfo.resourceMetrics.destQps = metrics.dest_qps || [];
                this.serviceInfo.resourceMetrics.srcQps = metrics.src_qps || [];

                // Add filesystem metrics
                this.serviceInfo.resourceMetrics.fsUsage = metrics.fs_usage || [];
                this.serviceInfo.resourceMetrics.fsWrite = metrics.fs_write || [];
                this.serviceInfo.resourceMetrics.fsRead = metrics.fs_read || [];

                // Update charts
                this.updateCharts();

                this.$message.success("Metrics data loaded successfully");
            } catch (error) {
                console.error("Failed to fetch metrics data:", error);
                this.$message.error("Unable to fetch metrics data, please check if the API is running properly");
            }
        },
        initCharts() {
            this.cpuChart = echarts.init(this.$refs.cpuChart);
            this.memoryChart = echarts.init(this.$refs.memoryChart);
            this.networkChart = echarts.init(this.$refs.networkChart);
            this.latencyChart = echarts.init(this.$refs.latencyChart);
            this.qpsChart = echarts.init(this.$refs.qpsChart);
            this.fsChart = echarts.init(this.$refs.fsChart);
        },
        updateCharts() {
            this.cpuChart.setOption(this.getCpuOption());
            this.memoryChart.setOption(this.getMemoryOption());
            this.networkChart.setOption(this.getNetworkOption());
            this.latencyChart.setOption(this.getLatencyOption());
            this.qpsChart.setOption(this.getQpsOption());
            this.fsChart.setOption(this.getFsOption());
        },
        async fetchPodDetails() {
            try {
                const response = await this.$http2.get(`/api/pod/${this.namespace}/${this.serviceName}`);
                // Only update Pod-related information, don't overwrite static resource data
                this.serviceInfo = {
                    ...this.serviceInfo, // Keep original static data
                    pod_name: response.data.pod_name,
                    namespace: response.data.namespace,
                    creation_time: response.data.creation_time,
                    node_name: response.data.node_name,
                    node_ip: response.data.node_ip,
                    pod_ip: response.data.pod_ip,
                    status: response.data.status
                };
            } catch (error) {
                console.error("Failed to fetch Pod details:", error);
                this.$message.error("Unable to fetch Pod details, please check if the API is running properly");
            }
        },
        async fetchPodContainers() {
            try {
                const response = await this.$http2.get(`/api/pod/containers/${this.namespace}/${this.serviceName}`);
                this.podContainers = response.data.containers;
                if (this.podContainers.length > 0) {
                    this.selectedContainer = this.podContainers[0];
                } else {
                    this.podContainers = ["default"];
                    this.selectedContainer = "default";
                }
            } catch (error) {
                console.error("Failed to fetch Pod container list:", error);
                this.podContainers = ["default"];
                this.selectedContainer = "default";
            }
        },
        goBack() {
            this.$router.go(-1);
        },
        getCpuOption() {
            return {
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: this.serviceInfo.resourceMetrics.timestamps },
                yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
                series: [{
                    name: 'CPU Usage',
                    type: 'line',
                    smooth: true,
                    data: this.serviceInfo.resourceMetrics.cpu,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
                            { offset: 1, color: 'rgba(64, 158, 255, 0)' }
                        ])
                    }
                }]
            };
        },
        getMemoryOption() {
            return {
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: this.serviceInfo.resourceMetrics.timestamps },
                yAxis: { type: 'value', axisLabel: { formatter: '{value} MB' } },
                series: [{
                    name: 'Memory Usage',
                    type: 'bar',
                    data: this.serviceInfo.resourceMetrics.memory,
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#36a3eb' },
                            { offset: 1, color: '#2ec7c9' }
                        ])
                    }
                }]
            };
        },
        getNetworkOption() {
            return {
                tooltip: { trigger: 'axis' },
                legend: { data: ['Received Traffic', 'Transmitted Traffic'] },
                xAxis: { type: 'category', data: this.serviceInfo.resourceMetrics.timestamps },
                yAxis: { type: 'value', axisLabel: { formatter: '{value} KB/s' } },
                series: [
                    {
                        name: 'Received Traffic',
                        type: 'line',
                        data: this.serviceInfo.resourceMetrics.netReceive,
                        smooth: true,
                        itemStyle: { color: '#91cc75' }
                    },
                    {
                        name: 'Transmitted Traffic',
                        type: 'line',
                        data: this.serviceInfo.resourceMetrics.netTransmit,
                        smooth: true,
                        itemStyle: { color: '#ee6666' }
                    }
                ]
            };
        },
        getLatencyOption() {
            return {
                tooltip: { trigger: 'axis' },
                legend: { data: ['P50 Latency', 'P90 Latency'] },
                xAxis: { type: 'category', data: this.serviceInfo.resourceMetrics.timestamps },
                yAxis: { type: 'value', axisLabel: { formatter: '{value} ms' } },
                series: [
                    {
                        name: 'P50 Latency',
                        type: 'line',
                        data: this.serviceInfo.resourceMetrics.destP50,
                        smooth: true,
                        itemStyle: { color: '#5470c6' }
                    },
                    {
                        name: 'P90 Latency',
                        type: 'line',
                        data: this.serviceInfo.resourceMetrics.destP90,
                        smooth: true,
                        itemStyle: { color: '#fac858' }
                    }
                ]
            };
        },
        getQpsOption() {
            return {
                tooltip: { trigger: 'axis' },
                legend: { data: ['Received QPS', 'Transmitted QPS'] },
                xAxis: { type: 'category', data: this.serviceInfo.resourceMetrics.timestamps },
                yAxis: { type: 'value' },
                series: [
                    {
                        name: 'Received QPS',
                        type: 'line',
                        data: this.serviceInfo.resourceMetrics.destQps,
                        smooth: true,
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(128, 0, 128, 0.4)' },
                                { offset: 1, color: 'rgba(128, 0, 128, 0)' }
                            ])
                        },
                        itemStyle: { color: '#9a60b4' }
                    },
                    {
                        name: 'Transmitted QPS',
                        type: 'line',
                        data: this.serviceInfo.resourceMetrics.srcQps,
                        smooth: true,
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(0, 128, 128, 0.4)' },
                                { offset: 1, color: 'rgba(0, 128, 128, 0)' }
                            ])
                        },
                        itemStyle: { color: '#3ba272' }
                    }
                ]
            };
        },
        getFsOption() {
            return {
                tooltip: { trigger: 'axis' },
                legend: { data: ['Usage (MB)', 'Write Time', 'Read Time'] },
                xAxis: { type: 'category', data: this.serviceInfo.resourceMetrics.timestamps },
                yAxis: [
                    { type: 'value', name: 'Usage', axisLabel: { formatter: '{value} MB' } },
                    { type: 'value', name: 'Operation Time', axisLabel: { formatter: '{value} s' } }
                ],
                series: [
                    {
                        name: 'Usage (MB)',
                        type: 'bar',
                        yAxisIndex: 0,
                        data: this.serviceInfo.resourceMetrics.fsUsage,
                        itemStyle: { color: '#73c0de' }
                    },
                    {
                        name: 'Write Time',
                        type: 'line',
                        yAxisIndex: 1,
                        data: this.serviceInfo.resourceMetrics.fsWrite,
                        itemStyle: { color: '#fc8452' }
                    },
                    {
                        name: 'Read Time',
                        type: 'line',
                        yAxisIndex: 1,
                        data: this.serviceInfo.resourceMetrics.fsRead,
                        itemStyle: { color: '#3ba272' }
                    }
                ]
            };
        },
        
        // Fetch Pod logs - Fix API path
        async fetchPodLogs() {
            this.logsLoading = true;
            this.logsError = null;
            this.podLogs = "";

            try {
                // First fetch Pod's container list
                await this.fetchPodContainers();
                
                // Use the same API path as the main page to fetch logs
                const response = await this.$http2.get(`/api/pod/logs/${this.namespace}/${this.serviceName}`, {
                    params: {
                        container: this.selectedContainer,
                        lines: this.logLines
                    }
                });
                
                if (response.data && response.data.logs) {
                    this.podLogs = response.data.logs;
                    if (this.podLogs) {
                        this.$message.success("Logs loaded successfully");
                    } else {
                        this.$message.info("No log data found");
                    }
                } else {
                    this.$message.warning("Log data format is incorrect");
                }
            } catch (error) {
                console.error("Failed to fetch logs:", error);
                this.logsError = "Unable to fetch log data, please try again later";
                this.$message.error(this.logsError);
            } finally {
                this.logsLoading = false;
            }
        },
        
        // Refresh logs
        refreshLogs() {
            this.fetchPodLogs();
        },

        // Download logs
        downloadLogs() {
            if (!this.podLogs) return;
            
            const blob = new Blob([this.podLogs], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${this.serviceName}-${this.selectedContainer}.log`;
            
            document.body.appendChild(a);
            a.click();
            
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        },
        
        // Fetch Pod's YAML definition
        async fetchPodYaml() {
            this.yamlLoading = true;
            
            try {
                const response = await this.$http2.get(`/api/yaml/pod/${this.namespace}/${this.serviceName}`);
                
                if (response.data && response.data.yaml) {
                    this.podYaml = response.data.yaml;
                    this.$message.success("YAML loaded successfully");
                } else {
                    this.$message.warning("YAML data format is incorrect");
                }
            } catch (error) {
                console.error("Failed to fetch YAML:", error);
                this.$message.error("Unable to fetch YAML, please try again later");
            } finally {
                this.yamlLoading = false;
            }
        },
        
        // Copy YAML to clipboard
        copyYaml() {
            if (!this.podYaml) return;
            
            const textArea = document.createElement('textarea');
            textArea.value = this.podYaml;
            document.body.appendChild(textArea);
            textArea.select();
            
            try {
                document.execCommand('copy');
                this.$message.success('YAML copied to clipboard successfully');
            } catch (err) {
                console.error('Unable to copy text:', err);
                this.$message.error('Copy failed, please copy manually');
            }
            
            document.body.removeChild(textArea);
        }
    },
    created() {
        this.fetchPodDetails(); // Load Pod detailed information
        this.fetchMetrics();    // Load metrics data
        this.fetchPodContainers(); // Get container list
    },
    mounted() {
        this.initCharts(); // Initialize ECharts charts

        // If the initial tab is logs, load logs
        if (this.activeTab === 'logs') {
            this.fetchPodLogs();
        }
        // If the initial tab is yaml, load YAML
        else if (this.activeTab === 'yaml') {
            this.fetchPodYaml();
        }

        // Listen for window size changes, redraw charts
        window.addEventListener('resize', () => {
            if (this.cpuChart) this.cpuChart.resize();
            if (this.memoryChart) this.memoryChart.resize();
            if (this.networkChart) this.networkChart.resize();
            if (this.latencyChart) this.latencyChart.resize();
            if (this.qpsChart) this.qpsChart.resize();
            if (this.fsChart) this.fsChart.resize();
        });
    },
    beforeDestroy() {
        // Destroy chart instances to avoid memory leaks
        if (this.cpuChart) this.cpuChart.dispose();
        if (this.memoryChart) this.memoryChart.dispose();
        if (this.networkChart) this.networkChart.dispose();
        if (this.latencyChart) this.latencyChart.dispose();
        if (this.qpsChart) this.qpsChart.dispose();
        if (this.fsChart) this.fsChart.dispose();

        // Remove event listeners
        window.removeEventListener('resize', () => { });
    },

};
</script>

<style scoped>
/* Keep original styles unchanged */
.header {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
}

.header h2 {
    margin-right: 15px;
}

.meta-row {
    margin-bottom: 20px;
}

.meta-item {
    background: #f5f7fa;
    padding: 15px;
    border-radius: 4px;
}

.meta-item label {
    color: #909399;
    font-size: 12px;
}

.chart-container {
    background: #fff;
    padding: 20px;
    border-radius: 4px;
    margin-bottom: 20px;
}

/* Overall card styles */
.box-card {
    margin: 20px;
    background-color: #fff;
    border-radius: 12px;
    /* Increase border radius */
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    /* Add shadow effect */
    padding: 20px;
}

/* Each metadata item */
.meta-row {
    margin-bottom: 20px;
}

.meta-item {
    background-color: #f9f9f9;
    padding: 15px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    /* Add small shadow for each item */
}

.meta-item label {
    font-weight: bold;
    color: #6c757d;
    font-size: 14px;
}

.meta-item div {
    font-size: 16px;
    color: #333;
    margin-top: 8px;
}

/* Chart container */
.chart-container {
    background-color: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}

.chart-container h3 {
    font-size: 16px;
    color: #333;
    margin-bottom: 15px;
}

.logs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.logs-actions {
    display: flex;
    gap: 10px;
}

.loading-container {
    padding: 20px 0;
}

.error-container {
    margin: 20px 0;
}

.empty-logs {
    padding: 40px 0;
}

/* Log content */
.log-content {
    background-color: #1e1e1e;
    color: #d4d4d4;
    padding: 15px;
    border-radius: 4px;
    overflow: auto;
    font-family: 'Courier New', Courier, monospace;
    height: 500px;
    white-space: pre-wrap;
    line-height: 1.5;
}

/* YAML related styles */
.yaml-container {
    margin-top: 10px;
}

.yaml-actions {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
}

.yaml-content {
    background-color: #1e1e1e;
    color: #d4d4d4;
    padding: 15px;
    border-radius: 4px;
    overflow: auto;
    font-family: 'Courier New', Courier, monospace;
    height: 500px;
    white-space: pre-wrap;
    line-height: 1.5;
}

/* Responsive design */
@media (max-width: 768px) {
    .header h2 {
        font-size: 18px;
    }

    .meta-item label {
        font-size: 12px;
    }

    .meta-item div {
        font-size: 14px;
    }

    .el-table th,
    .el-table td {
        padding: 8px 10px;
    }

    .chart-container {
        padding: 15px;
    }
    
    .logs-header {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .logs-actions {
        margin-top: 10px;
        width: 100%;
    }
}
</style>
