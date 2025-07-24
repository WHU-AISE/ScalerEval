<template>
  <div class="scaler-eval-page">
    <el-card class="page-card">
      <div class="page-header">
        <h1>🚀 ScalerEval - Elastic Scaling Performance Evaluation</h1>
        <p>Phased Microservice Auto-scaling Performance Evaluation Platform</p>
      </div>

      <!-- Configuration Area -->
      <el-card class="config-section">
        <div class="section-header">
          <h2>📋 Test Configuration</h2>
          <div class="header-actions">
            <!-- Phase 1: Environment Setup Button -->
            <el-button 
              type="primary" 
              size="large"
              @click="prepareEnvironment" 
              :disabled="!isBasicConfigValid || environmentStatus.status === 'preparing'"
              :loading="environmentStatus.status === 'preparing'"
            >
              <i class="el-icon-setting"></i> 
              {{ getEnvironmentButtonText() }}
            </el-button>
            
            <!-- Phase 2: Start Evaluation Button -->
            <el-button 
              type="success" 
              size="large"
              @click="startEvaluation" 
              :disabled="!isFullConfigValid || environmentStatus.status !== 'ready' || evaluationStatus.status === 'running'"
              :loading="evaluationStatus.status === 'running'"
            >
              <i class="el-icon-video-play"></i>
              {{ getEvaluationButtonText() }}
            </el-button>
            
            <!-- Reset Environment Button -->
            <el-button 
              type="danger" 
              size="large"
              @click="resetEnvironment" 
              :disabled="environmentStatus.status === 'preparing' || evaluationStatus.status === 'running'"
              plain
            >
              <i class="el-icon-delete"></i> Reset Environment
            </el-button>
          </div>
        </div>

        <!-- Configuration Content with Reduced Width -->
        <div class="config-content">
          <!-- First Row: Benchmark and Auto-scaler -->
          <el-row :gutter="24">
            <!-- Benchmark Selection -->
            <el-col :span="12">
              <div class="config-item">
                <h3>🏗️ Benchmark</h3>
                <el-select 
                  v-model="config.benchmark" 
                  placeholder="Select Benchmark"
                  size="large"
                  style="width: 100%"
                  @change="onBenchmarkChange"
                >
                  <el-option
                    v-for="benchmark in benchmarks"
                    :key="benchmark.name"
                    :label="benchmark.display_name"
                    :value="benchmark.name"
                  >
                    <div class="option-item">
                      <div class="option-title">{{ benchmark.display_name }}</div>
                      <div class="option-desc">{{ benchmark.description }}</div>
                      <div class="option-services">
                        Namespace: {{ benchmark.namespace }}
                        <span v-if="benchmark.sla"> | SLA: {{ benchmark.sla }}ms</span>
                      </div>
                    </div>
                  </el-option>
                </el-select>
              </div>
            </el-col>

            <!-- Auto-scaler Selection -->
            <el-col :span="12">
              <div class="config-item">
                <h3>⚙️ Auto-scaler</h3>
                <el-select 
                  v-model="config.scaler" 
                  placeholder="Select Auto-scaler"
                  size="large"
                  style="width: 100%"
                >
                  <el-option-group
                    v-for="group in scalerGroups"
                    :key="group.label"
                    :label="group.label"
                  >
                    <el-option
                      v-for="scaler in group.options"
                      :key="scaler.name"
                      :label="scaler.display_name"
                      :value="scaler.name"
                    >
                      <div class="option-item">
                        <div class="option-title">{{ scaler.display_name }}</div>
                        <div class="option-desc">{{ scaler.description }}</div>
                      </div>
                    </el-option>
                  </el-option-group>
                </el-select>
              </div>
            </el-col>
          </el-row>

          <!-- Second Row: Load Configuration - All in One -->
          <el-row style="margin-top: 20px;">
            <el-col :span="24">
              <div class="config-item">
                <h3>📊 Load Configuration</h3>
                
                <el-form label-position="top" size="small">
                  <el-row :gutter="24">
                    <!-- Workload Type -->
                    <el-col :span="8">
                      <el-form-item label="Workload Type">
                        <el-select v-model="config.workload" placeholder="Select Workload Type" style="width: 100%">
                          <el-option
                            v-for="workload in workloads"
                            :key="workload.name"
                            :label="workload.display_name"
                            :value="workload.name"
                          >
                            <div class="option-item">
                              <div class="option-title">{{ workload.display_name }}</div>
                              <div class="option-desc">{{ workload.description }}</div>
                            </div>
                          </el-option>
                        </el-select>
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-form>
              </div>
            </el-col>
          </el-row>

          <!-- Third Row: Execution Status -->
          <el-row :gutter="24" style="margin-top: 20px;">
            <!-- Environment Status Card -->
            <el-col :span="12">
              <div class="status-card environment-card">
                <div class="status-card-header">
                  <i class="el-icon-setting"></i>
                  <span>Environment Status</span>
                </div>
                <div class="status-card-content">
                  <div class="status-value">
                    <el-tag 
                      :type="getStatusTagType(environmentStatus.status)" 
                      size="large"
                    >
                      {{ getStatusText(environmentStatus.status) }}
                    </el-tag>
                  </div>
                  <div v-if="environmentStatus.current_step" class="status-step">
                    {{ environmentStatus.current_step }}
                  </div>
                  <div v-if="environmentStatus.progress > 0" class="status-progress">
                    <el-progress 
                      :percentage="environmentStatus.progress" 
                      :stroke-width="4"
                      :show-text="false"
                    ></el-progress>
                  </div>
                </div>
              </div>
            </el-col>

            <!-- Evaluation Status Card -->
            <el-col :span="12">
              <div class="status-card evaluation-card">
                <div class="status-card-header">
                  <i class="el-icon-video-play"></i>
                  <span>Evaluation Status</span>
                </div>
                <div class="status-card-content">
                  <div class="status-value">
                    <el-tag 
                      :type="getStatusTagType(evaluationStatus.status)" 
                      size="large"
                    >
                      {{ getStatusText(evaluationStatus.status) }}
                    </el-tag>
                  </div>
                  <div v-if="evaluationStatus.current_step" class="status-step">
                    {{ evaluationStatus.current_step }}
                  </div>
                  <div v-if="evaluationStatus.progress > 0" class="status-progress">
                    <el-progress 
                      :percentage="evaluationStatus.progress" 
                      :stroke-width="4"
                      :show-text="false"
                    ></el-progress>
                  </div>
                </div>
              </div>
            </el-col>
          </el-row>

          <!-- Operation Guide Area -->
          <div class="operation-guide">
            <el-alert
              :title="getOperationGuideTitle()"
              :type="getOperationGuideType()"
              :description="getOperationGuideDescription()"
              show-icon
              :closable="false"
            ></el-alert>
          </div>
        </div>
      </el-card>

      <!-- Dual Log System -->
      <el-card class="logs-section">
        <div class="section-header">
          <h2>📝 Real-time Log System</h2>
        </div>

        <el-tabs v-model="activeLogTab" @tab-click="handleTabClick">
          <!-- Environment Log Tab -->
          <el-tab-pane name="environment">
            <span slot="label">
              <i class="el-icon-setting"></i>
              Environment Logs
              <span v-if="environmentStatus.logs.length > 0" class="log-count">
                ({{ environmentStatus.logs.length }})
              </span>
            </span>
            
            <div class="logs-container">
              <div class="logs-header">
                <h3>Environment Setup and Initialization Logs</h3>
                <div class="logs-actions">
                  <el-button 
                    type="info" 
                    size="mini" 
                    @click="toggleAutoScroll('env')"
                  >
                    <i :class="autoScrollEnv ? 'el-icon-unlock' : 'el-icon-lock'"></i> 
                    {{ autoScrollEnv ? 'Stop' : 'Start' }} Auto-scroll
                  </el-button>
                  <el-button 
                    type="primary" 
                    size="mini" 
                    @click="clearLogs('environment')"
                    :disabled="environmentStatus.logs.length === 0"
                  >
                    <i class="el-icon-delete"></i> Clear Logs
                  </el-button>
                  <el-button 
                    type="success" 
                    size="mini" 
                    @click="downloadLogs('environment')"
                    :disabled="environmentStatus.logs.length === 0"
                  >
                    <i class="el-icon-download"></i> Download Logs
                  </el-button>
                </div>
              </div>
              
              <div 
                ref="envLogsOutput" 
                class="logs-output"
                :class="{ 'auto-scroll': autoScrollEnv }"
              >
                <div 
                  v-for="(log, index) in environmentStatus.logs" 
                  :key="index"
                  class="log-item"
                >
                  <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
                
                <div v-if="environmentStatus.logs.length === 0" class="empty-logs">
                  <el-empty description="No environment logs available" :image-size="80"></el-empty>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- Evaluation Log Tab -->
          <el-tab-pane name="evaluation">
            <span slot="label">
              <i class="el-icon-video-play"></i>
              Evaluation Logs
              <span v-if="evaluationStatus.logs.length > 0" class="log-count">
                ({{ evaluationStatus.logs.length }})
              </span>
            </span>
            
            <div class="logs-container">
              <div class="logs-header">
                <h3>Auto-scaler and Locust Evaluation Logs</h3>
                <div class="logs-actions">
                  <el-button 
                    type="info" 
                    size="mini" 
                    @click="toggleAutoScroll('eval')"
                  >
                    <i :class="autoScrollEval ? 'el-icon-unlock' : 'el-icon-lock'"></i> 
                    {{ autoScrollEval ? 'Stop' : 'Start' }} Auto-scroll
                  </el-button>
                  <el-button 
                    type="primary" 
                    size="mini" 
                    @click="clearLogs('evaluation')"
                    :disabled="evaluationStatus.logs.length === 0"
                  >
                    <i class="el-icon-delete"></i> Clear Logs
                  </el-button>
                  <el-button 
                    type="success" 
                    size="mini" 
                    @click="downloadLogs('evaluation')"
                    :disabled="evaluationStatus.logs.length === 0"
                  >
                    <i class="el-icon-download"></i> Download Logs
                  </el-button>
                </div>
              </div>
              
              <div 
                ref="evalLogsOutput" 
                class="logs-output"
                :class="{ 'auto-scroll': autoScrollEval }"
              >
                <div 
                  v-for="(log, index) in evaluationStatus.logs" 
                  :key="index"
                  class="log-item"
                >
                  <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                  <span class="log-message">{{ formatLogMessage(log) }}</span>
                </div>
                
                <div v-if="evaluationStatus.logs.length === 0" class="empty-logs">
                  <el-empty description="No evaluation logs available" :image-size="80"></el-empty>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- Evaluation Results Display -->
      <el-card class="results-section" v-if="evaluationStatus.status === 'completed' && evaluationStatus.results">
        <div class="section-header">
          <h2>📊 Evaluation Results</h2>
          <div class="results-actions">
            <el-button @click="resetTest" type="primary" plain>
              <i class="el-icon-refresh"></i> New Test
            </el-button>
            <el-button @click="exportResults" type="success" plain>
              <i class="el-icon-download"></i> Export Results
            </el-button>
          </div>
        </div>

        <el-row :gutter="20">
          <el-col :span="6">
            <div class="metric-card slo-card">
              <div class="metric-header">
                <i class="el-icon-warning"></i>
                <span>SLA Violation Rate</span>
              </div>
              <div class="metric-value">
                {{ (evaluationStatus.results.slo_violation_rate * 100).toFixed(1) }}%
              </div>
              <div class="metric-desc">Percentage of requests exceeding response time threshold</div>
            </div>
          </el-col>

          <el-col :span="6">
            <div class="metric-card success-card">
              <div class="metric-header">
                <i class="el-icon-check"></i>
                <span>Success Rate</span>
              </div>
              <div class="metric-value">
                {{ (evaluationStatus.results.success_rate * 100).toFixed(1) }}%
              </div>
              <div class="metric-desc">Percentage of requests completed successfully</div>
            </div>
          </el-col>

          <el-col :span="6">
            <div class="metric-card cpu-card">
              <div class="metric-header">
                <i class="el-icon-cpu"></i>
                <span>CPU Usage</span>
              </div>
              <div class="metric-value">
                {{ evaluationStatus.results.cpu_usage.toFixed(1) }}
              </div>
              <div class="metric-desc">Total CPU usage (millicores)</div>
            </div>
          </el-col>

          <el-col :span="6">
            <div class="metric-card memory-card">
              <div class="metric-header">
                <i class="el-icon-s-data"></i>
                <span>Memory Usage</span>
              </div>
              <div class="metric-value">
                {{ (evaluationStatus.results.memory_usage / 1024).toFixed(1) }} GB
              </div>
              <div class="metric-desc">Total memory usage</div>
            </div>
          </el-col>
        </el-row>

        <!-- Test Configuration Review -->
        <div class="test-summary">
          <h3>Test Configuration Review</h3>
          <el-descriptions :column="4" border>
            <el-descriptions-item label="Benchmark">{{ getBenchmarkName(config.benchmark) }}</el-descriptions-item>
            <el-descriptions-item label="Auto-scaler">{{ getScalerName(config.scaler) }}</el-descriptions-item>
            <el-descriptions-item label="Workload">{{ getWorkloadName(config.workload) }}</el-descriptions-item>
            <el-descriptions-item label="Test Duration">{{ config.duration / 60 }} minutes</el-descriptions-item>
            <el-descriptions-item label="Load Intensity">{{ getLoadDistName(config.load_dist) }}</el-descriptions-item>
            <el-descriptions-item label="Environment Status">
              <el-tag type="success">Ready</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Evaluation Status">
              <el-tag type="success">Completed</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-card>

    </el-card>
  </div>
</template>

<script>
export default {
  name: "ScalerEvalEnhanced",
  data() {
    return {
      // Configuration options
      config: {
        benchmark: '',
        scaler: '',
        workload: 'wiki',
        duration: 1200,    // 20 minutes, consistent with locustfile
        load_dist: '2'     // Medium load, consistent with locustfile
      },

      // Environment status
      environmentStatus: {
        status: 'idle', // idle, preparing, ready, error
        current_step: '',
        progress: 0,
        logs: []
      },

      // Evaluation status
      evaluationStatus: {
        status: 'idle', // idle, running, completed, error
        current_step: '',
        progress: 0,
        logs: [],
        results: null
      },

      // Option data
      benchmarks: [],
      scalers: [],
      workloads: [],
      loadDistributions: [],

      // History records
      testHistory: [],
      historyLoading: false,
      historySearchQuery: '',

      // UI state
      activeLogTab: 'environment',
      autoScrollEnv: true,
      autoScrollEval: true,

      // 🔧 New: REST API log polling related
      logPollingInterval: null,
      envLogPosition: 0,  // Environment log file read position
      evalLogPosition: 0, // Evaluation log file read position
      logPollingActive: true, // Whether to enable log polling

      // 🔧 Keep but unused WebSocket connections (commented but preserved)
      envWebSocket: null,
      evalWebSocket: null,

      // Polling timer
      statusPoller: null
    };
  },

  computed: {
    // Basic configuration validation (benchmark + auto-scaler)
    isBasicConfigValid() {
      return this.config.benchmark && this.config.scaler;
    },

    // Full configuration validation (including load configuration)
    isFullConfigValid() {
      return this.isBasicConfigValid && 
             this.config.workload
    },

    scalerGroups() {
      const groups = {
        'baseline': { label: 'Baseline', options: [] },
        'reactive': { label: 'Reactive', options: [] },
        'predictive': { label: 'Predictive', options: [] },
        'performance': { label: 'Performance-driven', options: [] },
        'custom': { label: 'Custom', options: [] }
      };

      this.scalers.forEach(scaler => {
        if (groups[scaler.type]) {
          groups[scaler.type].options.push(scaler);
        }
      });

      return Object.values(groups).filter(group => group.options.length > 0);
    },

    filteredHistory() {
      if (!this.historySearchQuery) return this.testHistory;
      
      const query = this.historySearchQuery.toLowerCase();
      return this.testHistory.filter(record => 
        record.benchmark.toLowerCase().includes(query) ||
        record.scaler.toLowerCase().includes(query) ||
        record.workload.toLowerCase().includes(query)
      );
    }
  },

  async mounted() {
    console.log('ScalerEval component mounting started...');
    
    try {
      console.log('1. Loading configuration options...');
      await this.loadConfigOptions();
            
      console.log('3. Checking current status...');
      await this.checkCurrentStatus();
      
      console.log('4. Starting REST API log polling...');
      this.startLogPolling();
      
      // 🔧 Comment out WebSocket initialization, switch to REST API polling
      // console.log('4. Initializing WebSocket...');
      // this.initWebSockets();
      
      console.log('5. Starting status polling...');
      this.startStatusPolling();
      
      console.log('ScalerEval component initialization completed!');
    } catch (error) {
      console.error('Component initialization failed:', error);
      this.$message.error('Page initialization failed, please refresh and try again');
    }
  },

  beforeDestroy() {
    // Clear status polling
    if (this.statusPoller) {
      clearInterval(this.statusPoller);
    }
    
    // 🔧 Clear log polling
    if (this.logPollingInterval) {
      clearInterval(this.logPollingInterval);
    }
    this.logPollingActive = false;
    
    // 🔧 Clear WebSocket connections (keep but commented out)
    // if (this.envWebSocket) {
    //   this.envWebSocket.close();
    // }
    // if (this.evalWebSocket) {
    //   this.evalWebSocket.close();
    // }
  },

  methods: {
    // ==================== Button Text Logic ====================
    
    getEnvironmentButtonText() {
      switch (this.environmentStatus.status) {
        case 'preparing':
          return 'Preparing Environment...';
        case 'ready':
          return 'Environment Ready';
        case 'error':
          return 'Restart Environment';
        default:
          return 'Start Environment';
      }
    },

    getEvaluationButtonText() {
      switch (this.evaluationStatus.status) {
        case 'running':
          return 'Evaluation Running...';
        case 'completed':
          return 'Start New Evaluation';
        case 'error':
          return 'Restart Evaluation';
        default:
          return 'Start Evaluation';
      }
    },

    // ==================== Status Display Logic ====================
    
    getCurrentStep() {
      if (this.environmentStatus.status === 'preparing' && this.environmentStatus.current_step) {
        return this.environmentStatus.current_step;
      }
      if (this.evaluationStatus.status === 'running' && this.evaluationStatus.current_step) {
        return this.evaluationStatus.current_step;
      }
      return '';
    },

    getCurrentProgress() {
      if (this.environmentStatus.status === 'preparing') {
        return this.environmentStatus.progress;
      }
      if (this.evaluationStatus.status === 'running') {
        return this.evaluationStatus.progress;
      }
      return 0;
    },

    // ==================== Operation Guide Logic ====================
    
    getOperationGuideTitle() {
      if (!this.isBasicConfigValid) {
        return 'Please configure basic parameters';
      }
      if (this.environmentStatus.status === 'idle') {
        return 'Step 1: Start Environment';
      }
      if (this.environmentStatus.status === 'preparing') {
        return 'Environment preparing, please wait...';
      }
      if (this.environmentStatus.status === 'ready' && !this.isFullConfigValid) {
        return 'Environment is ready, please complete load configuration';
      }
      if (this.environmentStatus.status === 'ready' && this.evaluationStatus.status === 'idle') {
        return 'Step 2: Start Evaluation';
      }
      if (this.evaluationStatus.status === 'running') {
        return 'Evaluation in progress, please wait...';
      }
      if (this.evaluationStatus.status === 'completed') {
        return 'Evaluation completed!';
      }
      if (this.environmentStatus.status === 'error' || this.evaluationStatus.status === 'error') {
        return 'An error occurred during execution. Please check the corresponding log tabs for detailed information, then click "Reset Environment" to start over';
      }
      return 'Please follow the interface prompts step by step';
    },

    getOperationGuideType() {
      if (this.environmentStatus.status === 'error' || this.evaluationStatus.status === 'error') {
        return 'error';
      }
      if (this.environmentStatus.status === 'preparing' || this.evaluationStatus.status === 'running') {
        return 'warning';
      }
      if (this.evaluationStatus.status === 'completed') {
        return 'success';
      }
      return 'info';
    },

    getOperationGuideDescription() {
      // Can add detailed descriptions as needed
      return '';
    },

    // ==================== Core Operation Methods ====================
    
    // Phase 1: Prepare Environment
    async prepareEnvironment() {
      if (!this.isBasicConfigValid) {
        this.$message.warning('Please select benchmark and auto-scaler first');
        return;
      }

      try {
        console.log('Starting environment preparation:', {
          benchmark: this.config.benchmark,
          scaler: this.config.scaler
        });
        
        const response = await this.$http2.post('/api/scaler-eval/prepare-environment', {
          benchmark: this.config.benchmark,
          scaler: this.config.scaler
        });
        
        console.log('Environment preparation request successful:', response.data);
        this.$message.success('Environment preparation started, please check environment logs for progress');
        this.activeLogTab = 'environment';
      } catch (error) {
        console.error('Failed to prepare environment:', error);
        this.$message.error('Environment preparation failed: ' + (error.response?.data?.detail || error.message));
      }
    },

    // Phase 2: Start Evaluation
    async startEvaluation() {
      if (!this.isFullConfigValid) {
        this.$message.warning('Please complete all configuration items');
        return;
      }

      if (this.environmentStatus.status !== 'ready') {
        this.$message.warning('Environment is not ready yet, please start environment first');
        return;
      }

      try {
        console.log('Starting evaluation:', {
          workload: this.config.workload
        });
        
        const response = await this.$http2.post('/api/scaler-eval/start-evaluation', {
          workload: this.config.workload
        });
        
        console.log('Evaluation start request successful:', response.data);
        this.$message.success('Evaluation started, please check evaluation logs for progress');
        this.activeLogTab = 'evaluation';
      } catch (error) {
        console.error('Failed to start evaluation:', error);
        this.$message.error('Evaluation start failed: ' + (error.response?.data?.detail || error.message));
      }
    },

    async resetEnvironment() {
      try {
        await this.$confirm('Are you sure you want to reset the environment? This will clean up all resources and reset the state.', 'Confirm Reset', {
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          type: 'warning'
        });

        console.log('Starting environment reset...');
        const response = await this.$http2.post('/api/scaler-eval/reset-environment');
        console.log('Reset environment response:', response.data);
        
        this.environmentStatus = {
          status: 'idle',
          current_step: '',
          progress: 0,
          config: {},
          logs: []
        };
        
        this.evaluationStatus = {
          status: 'idle',
          current_step: '',
          progress: 0,
          config: {},
          logs: [],
          results: null
        };

        this.envLogPosition = 0;
        this.evalLogPosition = 0;
        
        this.activeLogTab = 'environment';
        
        this.$message.success('Environment reset successful');
      } catch (error) {
        if (error !== 'cancel') {
          console.error('Failed to reset environment:', error);
          this.$message.error('Environment reset failed: ' + (error.response?.data?.detail || error.message));
        }
      }
    },

    async loadConfigOptions() {
      try {
        console.log('Starting to load configuration options...');
        
        const [benchmarkResponse, scalerResponse, workloadResponse] = await Promise.all([
          this.$http2.get('/api/scaler-eval/benchmarks'),
          this.$http2.get('/api/scaler-eval/scalers'),
          this.$http2.get('/api/scaler-eval/workloads')
        ]);

        console.log('Benchmarks response:', benchmarkResponse.data);
        console.log('Scalers response:', scalerResponse.data);
        console.log('Workloads response:', workloadResponse.data);

        this.benchmarks = benchmarkResponse.data.benchmarks || [];
        this.scalers = scalerResponse.data.scalers || [];
        this.workloads = workloadResponse.data.workloads || [];
        this.loadDistributions = workloadResponse.data.load_distributions || [];

        console.log('Configuration loading completed:', {
          benchmarks: this.benchmarks.length,
          scalers: this.scalers.length,
          workloads: this.workloads.length
        });

        // Set default values
        if (this.benchmarks.length > 0 && !this.config.benchmark) {
          this.config.benchmark = this.benchmarks[0].name;
        }
        if (this.scalers.length > 0 && !this.config.scaler) {
          this.config.scaler = this.scalers[0].name;
        }
      } catch (error) {
        console.error('Failed to load config options:', error);
        this.$message.error('Failed to load configuration options: ' + (error.response?.data?.detail || error.message));
      }
    },

    // 🔧 New: Start REST API log polling
    startLogPolling() {
      console.log('🚀 Starting REST API log polling...');
      this.logPollingActive = true;
      
      // Execute once immediately
      this.pollLogs();
      
      // Set up periodic polling, every 2 seconds
      this.logPollingInterval = setInterval(() => {
        if (this.logPollingActive) {
          this.pollLogs();
        }
      }, 2000);
    },

    // 🔧 New: Poll all logs
    async pollLogs() {
      try {
        // Poll both logs in parallel
        await Promise.all([
          this.pollEnvironmentLogs(),
          this.pollEvaluationLogs()
        ]);
      } catch (error) {
        // Polling failures don't need error display, just log to console
        console.debug('Log polling error:', error);
      }
    },

    // 🔧 New: Poll environment logs
    async pollEnvironmentLogs() {
      try {
        const response = await this.$http2.get('/api/logs/environment', {
          params: {
            last_position: this.envLogPosition
          }
        });

        const { logs, current_position } = response.data;
        
        if (logs && logs.length > 0) {
          console.log(`📨 Received ${logs.length} environment logs`);
          
          // Add new logs to existing log array
          this.environmentStatus.logs.push(...logs);
          
          // Limit log count
          if (this.environmentStatus.logs.length > 5000) {
            this.environmentStatus.logs = this.environmentStatus.logs.slice(-2500);
          }
          
          // Update file read position
          this.envLogPosition = current_position;
          
          // Auto-scroll
          if (this.autoScrollEnv && this.activeLogTab === 'environment') {
            this.$nextTick(() => {
              this.scrollToBottom('env');
            });
          }
        }
      } catch (error) {
        // Silently handle errors to avoid frequent error messages
        console.debug('Environment log polling error:', error);
      }
    },

    // 🔧 New: Poll evaluation logs
    async pollEvaluationLogs() {
      try {
        const response = await this.$http2.get('/api/logs/evaluation', {
          params: {
            last_position: this.evalLogPosition
          }
        });

        const { logs, current_position } = response.data;
        
        if (logs && logs.length > 0) {
          console.log(`📨 Received ${logs.length} evaluation logs`);
          
          // Add new logs to existing log array
          this.evaluationStatus.logs.push(...logs);
          
          // Limit log count
          if (this.evaluationStatus.logs.length > 1000) {
            this.evaluationStatus.logs = this.evaluationStatus.logs.slice(-500);
          }
          
          // Update file read position
          this.evalLogPosition = current_position;
          
          // Auto-scroll
          if (this.autoScrollEval && this.activeLogTab === 'evaluation') {
            this.$nextTick(() => {
              this.scrollToBottom('eval');
            });
          }
        }
      } catch (error) {
        // Silently handle errors to avoid frequent error messages
        console.debug('Evaluation log polling error:', error);
      }
    },

    // 🔧 Keep but comment out WebSocket initialization method
    /*
    initWebSockets() {
      try {
        console.log('🚀 Starting WebSocket connection initialization...');
        
        const envWsUrl = 'ws://localhost:8000/ws/scaler-eval/environment-logs';
        const evalWsUrl = 'ws://localhost:8000/ws/scaler-eval/evaluation-logs';
        
        console.log('🔗 Connecting environment log WebSocket:', envWsUrl);
               
        // Environment log WebSocket
        this.envWebSocket = new WebSocket(envWsUrl);
        
        this.envWebSocket.onopen = () => {
          console.log('✅ Environment log WebSocket connection successful');
        };
        
        this.envWebSocket.onmessage = (event) => {
          try {
            const logEntry = JSON.parse(event.data);
            console.log('📨 Received environment log:', logEntry);
            
            if (logEntry.message && logEntry.timestamp) {
              this.environmentStatus.logs.push(logEntry);
              
              if (this.environmentStatus.logs.length > 5000) {
                this.environmentStatus.logs = this.environmentStatus.logs.slice(-2500);
              }
              
              if (this.autoScrollEnv && this.activeLogTab === 'environment') {
                this.$nextTick(() => {
                  this.scrollToBottom('env');
                });
              }
              
              this.$forceUpdate();
            }
          } catch (error) {
            console.error('❌ Failed to parse environment log:', error);
          }
        };

        this.envWebSocket.onerror = (error) => {
          console.error('❌ Environment WebSocket error:', error);
        };

        this.envWebSocket.onclose = (event) => {
          console.log('🔌 Environment log WebSocket connection closed:', event.code, event.reason);
        };

        // Evaluation log WebSocket
        console.log('🔗 Connecting evaluation log WebSocket:', evalWsUrl);
        this.evalWebSocket = new WebSocket(evalWsUrl);
        
        this.evalWebSocket.onopen = () => {
          console.log('✅ Evaluation log WebSocket connection successful');
        };
        
        this.evalWebSocket.onmessage = (event) => {
          try {
            const logEntry = JSON.parse(event.data);
            console.log('📨 Received evaluation log:', logEntry);
            
            if (logEntry.message && logEntry.timestamp) {
              this.evaluationStatus.logs.push(logEntry);
              
              if (this.evaluationStatus.logs.length > 1000) {
                this.evaluationStatus.logs = this.evaluationStatus.logs.slice(-500);
              }
              
              if (this.autoScrollEval && this.activeLogTab === 'evaluation') {
                this.$nextTick(() => {
                  this.scrollToBottom('eval');
                });
              }
              
              this.$forceUpdate();
            }
          } catch (error) {
            console.error('❌ Failed to parse evaluation log:', error);
          }
        };

        this.evalWebSocket.onerror = (error) => {
          console.error('❌ Evaluation WebSocket error:', error);
        };

        this.evalWebSocket.onclose = (event) => {
          console.log('🔌 Evaluation log WebSocket connection closed:', event.code, event.reason);
        };

      } catch (error) {
        console.error('❌ WebSocket initialization failed:', error);
        this.$message.warning('Real-time log functionality may be unavailable');
      }
    },
    */

    // Check current status
    async checkCurrentStatus() {
      try {
        console.log('Checking current status...');
        
        const [envResponse, evalResponse] = await Promise.all([
          this.$http2.get('/api/scaler-eval/environment-status'),
          this.$http2.get('/api/scaler-eval/evaluation-status')
        ]);

        console.log('Environment status:', envResponse.data);
        console.log('Evaluation status:', evalResponse.data);

        // Update environment status, preserve existing logs
        this.environmentStatus = {
          ...this.environmentStatus,
          status: envResponse.data.status,
          current_step: envResponse.data.current_step,
          progress: envResponse.data.progress,
          config: envResponse.data.config || this.environmentStatus.config
        };

        // Update evaluation status, preserve existing logs
        this.evaluationStatus = {
          ...this.evaluationStatus,
          status: evalResponse.data.status,
          current_step: evalResponse.data.current_step,
          progress: evalResponse.data.progress,
          config: evalResponse.data.config || this.evaluationStatus.config,
          results: evalResponse.data.results
        };

        console.log('Status update completed:', {
          envStatus: this.environmentStatus.status,
          evalStatus: this.evaluationStatus.status
        });

      } catch (error) {
        console.error('Failed to check status:', error);
        this.$message.error('Status check failed: ' + (error.response?.data?.detail || error.message));
      }
    },

    // Start status polling
    startStatusPolling() {
      if (this.statusPoller) {
        clearInterval(this.statusPoller);
      }

      this.statusPoller = setInterval(async () => {
        await this.checkCurrentStatus();
                
        // Check environment status changes, automatically switch log tabs
        if (this.environmentStatus.status === 'preparing' && this.activeLogTab !== 'environment') {
          console.log('Environment preparing, switching to environment logs');
        }
        if (this.evaluationStatus.status === 'running' && this.activeLogTab !== 'evaluation') {
          console.log('Evaluation running, switching to evaluation logs');
        }
      }, 2000);  // Poll every 2 seconds
    },
    // ==================== Log Management Methods ====================

    // Benchmark change handler
    onBenchmarkChange() {
      console.log('Benchmark changed to:', this.config.benchmark);
    },

    // Tab click handler
    handleTabClick(tab) {
      this.activeLogTab = tab.name;
      
      // Auto-scroll to bottom when switching tabs
      this.$nextTick(() => {
        if (tab.name === 'environment' && this.autoScrollEnv) {
          this.scrollToBottom('env');
        } else if (tab.name === 'evaluation' && this.autoScrollEval) {
          this.scrollToBottom('eval');
        }
      });
    },

    // Toggle auto-scroll
    toggleAutoScroll(type) {
      if (type === 'env') {
        this.autoScrollEnv = !this.autoScrollEnv;
        if (this.autoScrollEnv) {
          this.$nextTick(() => this.scrollToBottom('env'));
        }
      } else {
        this.autoScrollEval = !this.autoScrollEval;
        if (this.autoScrollEval) {
          this.$nextTick(() => this.scrollToBottom('eval'));
        }
      }
    },

    // Scroll to bottom
    scrollToBottom(type) {
      const ref = type === 'env' ? 'envLogsOutput' : 'evalLogsOutput';
      if (this.$refs[ref]) {
        this.$refs[ref].scrollTop = this.$refs[ref].scrollHeight;
      }
    },

    // Clear logs
    clearLogs(type) {
      if (type === 'environment') {
        this.environmentStatus.logs = [];
        // 🔧 Reset file read position
        this.envLogPosition = 0;
      } else {
        this.evaluationStatus.logs = [];
        // 🔧 Reset file read position
        this.evalLogPosition = 0;
      }
    },

    // Download logs
    downloadLogs(type) {
      const logs = type === 'environment' ? this.environmentStatus.logs : this.evaluationStatus.logs;
      
      if (logs.length === 0) return;
      
      const logContent = logs.map(log => 
        `[${this.formatLogTime(log.timestamp)}] ${log.message}`
      ).join('\n');
      
      const blob = new Blob([logContent], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `scaler-eval-${type}-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
      
      document.body.appendChild(a);
      a.click();
      
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },

    // ==================== Result Handling Methods ====================

    // Reset test
    resetTest() {
      this.evaluationStatus = {
        status: 'idle',
        current_step: '',
        progress: 0,
        logs: [],
        results: null
      };
    },

    // Export results
    exportResults() {
      if (!this.evaluationStatus.results) return;
      
      const results = {
        config: this.config,
        environmentStatus: this.environmentStatus,
        evaluationStatus: this.evaluationStatus
      };
      
      const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `scaler-eval-results-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
      
      document.body.appendChild(a);
      a.click();
      
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },

    // ==================== Utility Methods ====================
    
    getStatusTagType(status) {
      const typeMap = {
        'idle': '',
        'preparing': 'warning',
        'ready': 'success',
        'running': 'warning',
        'completed': 'success',
        'error': 'danger'
      };
      return typeMap[status] || '';
    },

    getStatusText(status) {
      const textMap = {
        'idle': 'Idle',
        'preparing': 'Preparing',
        'ready': 'Ready',
        'running': 'Running',
        'completed': 'Completed',
        'error': 'Error'
      };
      return textMap[status] || status;
    },

    // 🔧 Simplified log style determination - no longer use complex style classes
    getLogClass(log) {
      // Uniformly return basic style class, no longer distinguish different types
      return 'unified';
    },

    // 🔧 Simplified log message formatting - directly display original message
    formatLogMessage(log) {
      return log.message || '';
    },

    formatLogTime(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    },

    formatTime(timestamp) {
      if (!timestamp) return '';
      return new Date(timestamp).toLocaleString('en-US');
    },

    getBenchmarkName(name) {
      const benchmark = this.benchmarks.find(b => b.name === name);
      return benchmark ? benchmark.display_name : name;
    },

    getScalerName(name) {
      const scaler = this.scalers.find(s => s.name === name);
      return scaler ? scaler.display_name : name;
    },

    getWorkloadName(name) {
      const workload = this.workloads.find(w => w.name === name);
      return workload ? workload.display_name : name;
    },

    getLoadDistName(value) {
      const dist = this.loadDistributions.find(d => d.value === value);
      return dist ? dist.label : value;
    },

    getScalerTagType(scalerName) {
      if (scalerName === 'None') return '';
      if (scalerName.startsWith('KHPA')) return 'warning';
      if (scalerName === 'Showar') return 'success';
      if (scalerName === 'PBScaler') return 'danger';
      return 'info';
    },

    getSLAClass(rate) {
      if (rate < 0.05) return 'text-success';
      if (rate < 0.1) return 'text-warning';
      return 'text-danger';
    },

    getSuccessClass(rate) {
      if (rate >= 0.99) return 'text-success';
      if (rate >= 0.95) return 'text-warning';
      return 'text-danger';
    }
  }
};
</script>

<style scoped>
.scaler-eval-page {
  padding: 0px 20px 20px 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.page-card {
  max-width: 1600px;
  margin: 0 auto;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.page-header {
  text-align: center;
  padding: 20px 0 30px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-header p {
  color: #7f8c8d;
  font-size: 16px;
}

.logs-section {
  margin: 0 auto;
  height: 800px;
  max-width: 1400px;
  margin-bottom: 30px;
  border-radius: 8px;
}


.config-section,
.logs-section,
.results-section,
.history-section {
  margin: 0 auto;
  max-width: 1400px;
  margin-bottom: 30px;
  border-radius: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.section-header h2 {
  font-size: 20px;
  color: #2c3e50;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 15px;
  align-items: center;
}

.results-actions,
.history-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.config-item {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  transition: border-color 0.3s ease, transform 0.2s ease;
}

.config-item:hover {
  border-color: #409EFF;
  transform: translateY(-2px);
}

.config-item h3 {
  font-size: 16px;
  color: #495057;
  margin-bottom: 15px;
}

.option-item {
  padding: 8px 0;
}

.option-title {
  font-weight: bold;
  color: #2c3e50;
}

.option-desc {
  font-size: 12px;
  color: #7f8c8d;
  margin-top: 2px;
}

.option-services {
  font-size: 11px;
  color: #17a2b8;
  margin-top: 2px;
}

/* 🔧 New: Execution status card styles */
.status-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: all 0.3s ease;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.status-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  border-color: #409EFF;
}

.environment-card {
  border-left: 4px solid #409EFF;
}

.evaluation-card {
  border-left: 4px solid #67C23A;
}

.status-card-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 15px;
}

.status-card-header i {
  font-size: 18px;
  color: #409EFF;
}

.evaluation-card .status-card-header i {
  color: #67C23A;
}

.status-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.status-value {
  margin-bottom: 8px;
}

.status-step {
  font-size: 12px;
  color: #606266;
  text-align: center;
  line-height: 1.4;
  max-width: 100%;
  word-wrap: break-word;
}

.status-progress {
  width: 100%;
  margin-top: 8px;
}

/* Status display styles */
/* Operation guide styles */
.operation-guide {
  margin-top: 20px;
  padding: 15px;
  border-radius: 8px;
}

/* 🔧 New: Unified log count styles, replacing red dot */
.log-count {
  margin-left: 8px;
  color: #409EFF;
  font-weight: 500;
  font-size: 12px;
}

/* Log-related styles */
.logs-container {
  margin-top: 10px;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.logs-header h3 {
  font-size: 16px;
  color: #2c3e50;
  margin: 0;
}

.logs-actions {
  display: flex;
  gap: 10px;
}

.logs-output {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  height: 600px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid #ddd;
}

.logs-output.auto-scroll {
  scroll-behavior: smooth;
}

/* 🔧 Unified log styles - remove all color differences */
.log-item {
  margin-bottom: 5px;
  word-break: break-all;
  color: #e8f4f8; /* Unified bright color for easy reading */
}

/* 🔧 Remove all different level color distinctions */
.log-item.info,
.log-item.error,
.log-item.success,
.log-item.warning,
.log-item.locust,
.log-item.scaler,
.log-item.unified {
  color: #e8f4f8; /* Unified color */
  font-weight: normal; /* Unified font weight */
}

.log-time {
  color: #95a5a6;
  margin-right: 10px;
  font-size: 12px;
}

.log-message {
  color: inherit;
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #7f8c8d;
}

/* Metric card styles */
.metric-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  margin-bottom: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.slo-card {
  height: 150px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.success-card {
  height: 150px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.cpu-card {
  height: 150px;
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.memory-card {
  height: 150px;
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
}

.metric-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 15px;
  font-size: 14px;
  opacity: 0.9;
}

.metric-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.metric-desc {
  font-size: 12px;
  opacity: 0.8;
}

.test-summary {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.test-summary h3 {
  font-size: 16px;
  color: #2c3e50;
  margin-bottom: 15px;
}

/* History record styles */
.empty-history {
  padding: 30px 0;
}

.text-success {
  color: #67c23a;
  font-weight: bold;
}

.text-warning {
  color: #e6a23c;
  font-weight: bold;
}

.text-danger {
  color: #f56c6c;
  font-weight: bold;
}

/* Custom scrollbar */
.logs-output::-webkit-scrollbar {
  width: 8px;
}

.logs-output::-webkit-scrollbar-track {
  background: #34495e;
  border-radius: 4px;
}

.logs-output::-webkit-scrollbar-thumb {
  background: #7f8c8d;
  border-radius: 4px;
}

.logs-output::-webkit-scrollbar-thumb:hover {
  background: #95a5a6;
}

/* Responsive design */
@media (max-width: 768px) {
  .scaler-eval-page {
    padding: 10px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }

  .header-actions {
    flex-direction: column;
    gap: 10px;
    width: 100%;
  }

  .header-actions .el-button {
    width: 100%;
  }

  .metric-value {
    font-size: 24px;
  }

  .config-item {
    padding: 15px;
  }

  .logs-output {
    height: 300px;
    font-size: 12px;
  }

  .results-actions,
  .history-actions {
    flex-wrap: wrap;
  }
}
</style>