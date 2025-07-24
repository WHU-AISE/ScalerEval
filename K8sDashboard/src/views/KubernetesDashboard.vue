<template>
  <div class="kubernetes-dashboard">
    <!-- Overview Dashboard -->
    <div class="overview-dashboard">
      <div class="overview-grid">
        <div class="metric-card namespaces-card">
          <div class="metric-icon">
            <i class="el-icon-s-grid"></i>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ namespaces.length }}</div>
            <div class="metric-label">Total Namespaces</div>
          </div>
        </div>

        <div class="metric-card pods-card">
          <div class="metric-icon">
            <i class="el-icon-box"></i>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ totalPods }}</div>
            <div class="metric-label">Total Pods</div>
          </div>
        </div>

        <div class="metric-card deployments-card">
          <div class="metric-icon">
            <i class="el-icon-s-operation"></i>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ totalDeployments }}</div>
            <div class="metric-label">Deployments</div>
          </div>
        </div>

        <div class="metric-card services-card">
          <div class="metric-icon">
            <i class="el-icon-connection"></i>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ totalServices }}</div>
            <div class="metric-label">Services</div>
          </div>
        </div>
      </div>
    </div>

    <div class="namespace-section">
      <div class="section-header">
        <div class="section-title">
          <h2>Kubernetes Namespaces</h2>
          <p class="section-subtitle">Manage and explore your cluster namespaces</p>
        </div>
        <div class="section-actions">
          <el-input
            v-model="searchQuery"
            placeholder="Search Namespace"
            prefix-icon="el-icon-search"
            clearable
            class="search-input"
          ></el-input>
          <el-button type="primary" @click="fetchNamespaces" :loading="loading.namespaces" class="refresh-btn">
            <i class="el-icon-refresh"></i> Refresh
          </el-button>
        </div>
      </div>

      <!-- Namespace Grid -->
      <div class="namespaces-grid" v-loading="loading.namespaces">
        <div 
          v-for="namespace in filteredNamespaces" 
          :key="namespace.name"
          class="namespace-card"
          :class="{ 'selected': selectedNamespace === namespace.name }"
          @click="handleNamespaceClick(namespace)"
        >
          <div class="namespace-header">
            <div class="namespace-info">
              <el-tag 
                size="large" 
                :type="getNamespaceTagType(namespace.name)"
                class="namespace-tag"
              >
                {{ namespace.name }}
              </el-tag>
              <span class="namespace-index">#{{ namespace.index }}</span>
            </div>
            <el-dropdown @command="command => handleNamespaceCommand(command, namespace)" trigger="click">
              <el-button size="mini" type="text" class="namespace-menu">
                <i class="el-icon-more"></i>
              </el-button>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item command="view-details">
                  <i class="el-icon-info"></i> View Details
                </el-dropdown-item>
                <el-dropdown-item command="view-yaml">
                  <i class="el-icon-document"></i> View YAML
                </el-dropdown-item>
                <el-dropdown-item command="pods">
                  <i class="el-icon-box"></i> View Pods
                </el-dropdown-item>
              </el-dropdown-menu>
            </el-dropdown>
          </div>
          
          <div class="namespace-stats">
            <div class="stat-item" v-if="getNamespaceDeploymentCount(namespace.name)">
              <i class="el-icon-s-operation"></i>
              <span>{{ getNamespaceDeploymentCount(namespace.name) }} Deployments</span>
            </div>
            <div class="stat-item" v-if="getNamespacePodCount(namespace.name)">
              <i class="el-icon-box"></i>
              <span>{{ getNamespacePodCount(namespace.name) }} Pods</span>
            </div>
          </div>

          <div class="namespace-status">
            <div class="status-indicator active"></div>
            <span class="status-text">Active</span>
          </div>
        </div>
      </div>

      <div v-if="filteredNamespaces.length === 0 && !loading.namespaces" class="empty-state">
        <div class="empty-illustration">
          <i class="el-icon-s-grid"></i>
        </div>
        <h3>No namespaces found</h3>
        <p>Try adjusting your search criteria</p>
      </div>
    </div>

    <!-- Deployments Section -->
    <div class="deployments-section" v-if="selectedNamespace">
      <div class="section-header">
        <div class="section-title">
          <h2>
            Deployments in
            <el-tag type="success" class="namespace-highlight">{{ selectedNamespace }}</el-tag>
          </h2>
          <p class="section-subtitle">Manage applications in this namespace</p>
        </div>
        <div class="section-actions">
          <el-input
            v-model="deploymentSearchQuery"
            placeholder="Search Deployment"
            prefix-icon="el-icon-search"
            clearable
            class="search-input"
          ></el-input>
          <el-button type="primary" @click="handleNamespaceClick({ name: selectedNamespace })" :loading="loading.deployments">
            <i class="el-icon-refresh"></i> Refresh
          </el-button>
          <el-button type="success" @click="createDeployment" class="create-btn">
            <i class="el-icon-plus"></i> Create
          </el-button>
        </div>
      </div>

      <div v-loading="loading.deployments" class="deployments-container">
        <div v-if="filteredDeployments.length > 0" class="deployments-list">
          <el-card
            v-for="deployment in filteredDeployments"
            :key="deployment.name"
            class="deployment-card"
            @click.native="viewDeploymentDetails(deployment)"
          >
            <div class="deployment-header">
              <h3 class="deployment-title">{{ deployment.name }}</h3>
              <el-tag size="mini" :type="getStatusType(deployment.status)" class="status-tag">
                {{ deployment.status || 'Unknown' }}
              </el-tag>
            </div>
            <div class="deployment-info">
              <div class="info-item">
                <i class="el-icon-s-operation"></i>
                <span>Replicas: {{ deployment.currentReplicas || 0 }}/{{ deployment.desiredReplicas || 0 }}</span>
              </div>
              <div class="info-item">
                <i class="el-icon-time"></i>
                <span>Uptime: {{ deployment.uptime || 'N/A' }}</span>
              </div>
            </div>
            <div class="deployment-actions">
              <el-button size="mini" type="text" @click.stop="viewDeploymentYaml(deployment)">
                YAML
              </el-button>
              <el-button size="mini" type="text" @click.stop="restartDeployment(deployment)">
                Restart
              </el-button>
              <el-button size="mini" type="text" @click.stop="scaleDeployment(deployment)">
                Scale
              </el-button>
            </div>
          </el-card>
        </div>

        <div v-else-if="!loading.deployments" class="empty-state">
          <div class="empty-illustration">
            <i class="el-icon-s-operation"></i>
          </div>
          <h3>No Deployments found</h3>
          <p>Create your first deployment to get started</p>
          <el-button type="primary" @click="createDeployment" class="empty-action-btn">
            <i class="el-icon-plus"></i> Create Deployment
          </el-button>
        </div>
      </div>

      <div class="pods-action">
        <el-button type="primary" @click="fetchPods" :loading="loading.pods" class="view-pods-btn">
          <i class="el-icon-view"></i> View all Pods in this namespace
        </el-button>
      </div>
    </div>

    <!-- Pods Section -->
    <div class="pods-section" v-if="pods.length > 0 || loading.pods">
      <div class="section-header">
        <div class="section-title">
          <h2>
            Pods in 
            <el-tag type="success" class="namespace-highlight">{{ selectedNamespace }}</el-tag>
          </h2>
          <p class="section-subtitle">Running container instances</p>
        </div>
        <div class="section-actions">
          <el-input
            v-model="podSearchQuery"
            placeholder="Search Pod"
            prefix-icon="el-icon-search"
            clearable
            class="search-input"
          ></el-input>
          <el-button type="primary" @click="fetchPods" :loading="loading.pods">
            <i class="el-icon-refresh"></i> Refresh
          </el-button>
        </div>
      </div>

      <div class="modern-table-container">
        <el-table
          :data="filteredPods"
          style="width: 100%"
          v-loading="loading.pods"
          class="modern-table"
        >
          <el-table-column prop="name" label="Pod Name" min-width="200">
            <template #default="{ row }">
              <router-link
                :to="{
                  name: 'ServiceDetail',
                  params: {
                    namespace: selectedNamespace,
                    serviceName: row.name
                  }
                }"
                class="pod-link"
              >
                <i class="el-icon-box"></i>
                <span class="pod-name-text">{{ row.name }}</span>
              </router-link>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="Status" width="100">
            <template #default="{ row }">
              <el-tag :type="getPodStatusType(row.status)" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="ip" label="Pod IP" width="130"></el-table-column>
          <el-table-column prop="node" label="Node" min-width="120"></el-table-column>
          <el-table-column prop="restarts" label="Restarts" width="80" align="center">
            <template #default="{ row }">
              <span class="restart-count" :class="{ 'high-restarts': row.restarts > 5 }">
                {{ row.restarts }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="creation_time" label="Creation Time" width="130">
            <template #default="{ row }">
              <span class="creation-time">{{ formatCreationTime(row.creation_time) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="age" label="Uptime" width="80"></el-table-column>
          <el-table-column label="Operation" width="200">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button size="mini" type="text" @click="viewPodLogs(row)" class="table-action-btn">
                  <i class="el-icon-document"></i> Logs
                </el-button>
                <el-button size="mini" type="text" @click="viewPodYaml(row)" class="table-action-btn">
                  <i class="el-icon-view"></i> YAML
                </el-button>
                <el-button 
                  size="mini" 
                  type="text" 
                  @click="deletePod(row)" 
                  :disabled="row.status === 'Terminating'"
                  class="table-action-btn danger"
                >
                  <i class="el-icon-delete"></i> Delete
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-if="filteredPods.length === 0 && !loading.pods" class="empty-state">
        <div class="empty-illustration">
          <i class="el-icon-box"></i>
        </div>
        <h3>No pods found</h3>
        <p>No pods are currently running in this namespace</p>
      </div>
    </div>

    <!-- Namespace Details Dialog -->
    <el-dialog 
      title="Namespace Details" 
      :visible.sync="namespaceDetailsVisible" 
      width="85%" 
      top="5vh"
    >
      <div v-loading="loading.namespaceDetails">
        <div v-if="namespaceDetails">
          <!-- Basic Information -->
          <div class="details-section">
            <h3>Basic Information</h3>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <strong>Namespace:</strong> {{ namespaceDetails.name }}
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <strong>Deployments:</strong> {{ namespaceDetails.statistics.deploymentCount }}
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <strong>Pods:</strong> {{ namespaceDetails.statistics.podCount }}
                </div>
              </el-col>
            </el-row>
          </div>

          <!-- Tab Content -->
          <el-tabs>
            <!-- Deployment List -->
            <el-tab-pane label="Deployments" name="deployments">
              <el-table :data="namespaceDetails.deployments" style="width: 100%" max-height="300">
                <el-table-column prop="name" label="Name" width="180"></el-table-column>
                <el-table-column prop="status" label="Status" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getStatusType(row.status)" size="small">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="currentReplicas" label="Current" width="80"></el-table-column>
                <el-table-column prop="desiredReplicas" label="Desired" width="80"></el-table-column>
                <el-table-column prop="uptime" label="Uptime" width="100"></el-table-column>
                <el-table-column label="Operation" width="120">
                  <template #default="{ row }">
                    <el-button size="mini" type="text" @click="viewDeploymentDetails(row)">
                      Details
                    </el-button>
                    <el-button size="mini" type="text" @click="viewDeploymentYaml(row)">
                      YAML
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <!-- Pods List -->
            <el-tab-pane label="Pods" name="pods">
              <el-table :data="namespaceDetails.pods" style="width: 100%" max-height="300">
                <el-table-column prop="name" label="Name" min-width="180">
                  <template #default="{ row }">
                    <router-link
                      :to="{
                        name: 'ServiceDetail',
                        params: {
                          namespace: namespaceDetails.name,
                          serviceName: row.name
                        }
                      }"
                      class="pod-link"
                    >
                      {{ row.name }}
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Status" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getPodStatusType(row.status)" size="small">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="ip" label="IP" width="120"></el-table-column>
                <el-table-column prop="node" label="Node" min-width="150"></el-table-column>
                <el-table-column prop="restarts" label="Restarts" width="150" align="center"></el-table-column>
                <el-table-column prop="age" label="Age" width="120"></el-table-column>
              </el-table>
            </el-tab-pane>

            <!-- YAML -->
            <el-tab-pane label="YAML" name="yaml">
              <pre class="yaml-content">{{ namespaceDetails.yaml }}</pre>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
      
      <span slot="footer" class="dialog-footer">
        <el-button @click="namespaceDetailsVisible = false">Close</el-button>
      </span>
    </el-dialog>

    <!-- Deployment Details Dialog -->
    <el-dialog 
      title="Deployment Details" 
      :visible.sync="deploymentDetailsVisible" 
      width="85%" 
      top="5vh"
    >
      <div v-loading="loading.deploymentDetails">
        <div v-if="deploymentDetails">
          <!-- Basic Information -->
          <div class="details-section">
            <h3>Basic Information</h3>
            <el-row :gutter="20">
              <el-col :span="6">
                <div class="info-item">
                  <strong>Name:</strong> {{ deploymentDetails.name }}
                </div>
              </el-col>
              <el-col :span="6">
                <div class="info-item">
                  <strong>Namespace:</strong> {{ deploymentDetails.namespace }}
                </div>
              </el-col>
              <el-col :span="6">
                <div class="info-item">
                  <strong>Status:</strong> 
                  <el-tag :type="getStatusType(deploymentDetails.status)" size="small">
                    {{ deploymentDetails.status }}
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="info-item">
                  <strong>Uptime:</strong> {{ deploymentDetails.uptime }}
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 15px;">
              <el-col :span="6">
                <div class="info-item">
                  <strong>Replicas:</strong> {{ deploymentDetails.currentReplicas }}/{{ deploymentDetails.desiredReplicas }}
                </div>
              </el-col>
            </el-row>
          </div>

          <!-- Tab Content -->
          <el-tabs>
            <!-- Related Pods -->
            <el-tab-pane label="Related Pods" name="pods">
              <el-table :data="deploymentDetails.relatedPods" style="width: 100%" max-height="300">
                <el-table-column prop="name" label="Pod Name" min-width="230">
                  <template #default="{ row }">
                    <router-link
                      :to="{
                        name: 'ServiceDetail',
                        params: {
                          namespace: deploymentDetails.namespace,
                          serviceName: row.name
                        }
                      }"
                      class="pod-link"
                    >
                      {{ row.name }}
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Status" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getPodStatusType(row.status)" size="small">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="ip" label="Pod IP" width="120"></el-table-column>
                <el-table-column prop="node" label="Node" min-width="140"></el-table-column>
                <el-table-column prop="restarts" label="Restarts" width="120" align="center"></el-table-column>
                <el-table-column prop="age" label="Age" width="120"></el-table-column>
                <el-table-column label="Operation" width="120">
                  <template #default="{ row }">
                    <el-button size="mini" type="text" @click="viewPodLogs(row)">
                      Logs
                    </el-button>
                    <el-button size="mini" type="text" @click="viewPodYaml(row)">
                      YAML
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <!-- Performance Metrics -->
            <el-tab-pane label="Metrics" name="metrics" v-if="deploymentDetails.metrics">
              <div class="metrics-grid">
                <div class="metric-card" v-if="deploymentDetails.metrics.metrics.cpu_usage">
                  <h4>CPU Usage</h4>
                  <div class="metric-value">
                    {{ (deploymentDetails.metrics.metrics.cpu_usage.slice(-1)[0] || 0).toFixed(2) }}m
                  </div>
                </div>
                <div class="metric-card" v-if="deploymentDetails.metrics.metrics.mem_usage">
                  <h4>Memory Usage</h4>
                  <div class="metric-value">
                    {{ (deploymentDetails.metrics.metrics.mem_usage.slice(-1)[0] || 0).toFixed(2) }}MB
                  </div>
                </div>
                <div class="metric-card" v-if="deploymentDetails.metrics.metrics.dest_qps">
                  <h4>QPS</h4>
                  <div class="metric-value">
                    {{ (deploymentDetails.metrics.metrics.dest_qps.slice(-1)[0] || 0).toFixed(2) }}
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- YAML -->
            <el-tab-pane label="YAML" name="yaml">
              <pre class="yaml-content">{{ deploymentDetails.yaml }}</pre>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
      
      <span slot="footer" class="dialog-footer">
        <el-button @click="deploymentDetailsVisible = false">Close</el-button>
        <el-button type="primary" @click="restartDeployment(deploymentDetails)" :loading="loading.restart">
          Restart
        </el-button>
        <el-button type="warning" @click="scaleDeployment(deploymentDetails)">
          Scale
        </el-button>
      </span>
    </el-dialog>

    <!-- YAML View Dialog -->
    <el-dialog title="VIEW YAML" :visible.sync="yamlDialogVisible" width="80%" top="5vh">
      <div v-loading="loading.yaml">
        <pre class="yaml-content">{{ yamlContent }}</pre>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="yamlDialogVisible = false">Close</el-button>
        <el-button type="primary" @click="copyYaml">Copy</el-button>
      </span>
    </el-dialog>

    <!-- Pod Logs View Dialog -->
    <el-dialog title="Pod Logs" :visible.sync="logDialogVisible" width="80%" top="5vh">
      <div v-loading="loading.logs">
        <el-form size="small" inline>
          <el-form-item label="Container">
            <el-select v-model="selectedContainer" placeholder="Select Container">
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
            <el-button type="primary" @click="refreshLogs" size="small">Refresh Logs</el-button>
            <el-button type="success" @click="downloadLogs" size="small" :disabled="!podLogs">Download Logs</el-button>
          </el-form-item>
        </el-form>
        <pre v-if="podLogs" class="log-content">{{ podLogs }}</pre>
        <el-empty v-else description="No log data available"></el-empty>
      </div>
    </el-dialog>

    <!-- Scale Deployment Dialog -->
    <el-dialog title="Set Replica Count" :visible.sync="scaleDialogVisible" width="30%">
      <el-form>
        <el-form-item label="Deployment">
          <strong>{{ selectedDeployment ? selectedDeployment.name : '' }}</strong>
        </el-form-item>
        <el-form-item label="Replica Count">
          <el-input-number
            v-model="replicaCount"
            :min="0"
            :max="20"
            :step="1"
          ></el-input-number>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="scaleDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="confirmScale" :loading="loading.scale">Confirm</el-button>
      </span>
    </el-dialog>

    <!-- Create Deployment Dialog -->
    <el-dialog title="Create Deployment" :visible.sync="createDialogVisible" width="80%">
      <el-tabs v-model="createTabActive">
        <el-tab-pane label="Form" name="form">
          <el-form :model="deploymentForm" label-width="120px">
            <el-form-item label="Name">
              <el-input v-model="deploymentForm.name" placeholder="Enter Deployment name"></el-input>
            </el-form-item>
            <el-form-item label="Image">
              <el-input v-model="deploymentForm.image" placeholder="Enter container image (e.g.: nginx:latest)"></el-input>
            </el-form-item>
            <el-form-item label="Replicas">
              <el-input-number v-model="deploymentForm.replicas" :min="1" :max="10"></el-input-number>
            </el-form-item>
            <el-form-item label="Port">
              <el-input-number v-model="deploymentForm.port" :min="1" :max="65535"></el-input-number>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="YAML" name="yaml">
          <el-input
            type="textarea"
            v-model="deploymentForm.yaml"
            :rows="15"
            placeholder="Enter Deployment YAML"
          ></el-input>
        </el-tab-pane>
      </el-tabs>
      <span slot="footer" class="dialog-footer">
        <el-button @click="createDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="confirmCreateDeployment" :loading="loading.create">Create</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: "Namespaces",
  data() {
    return {
      namespaces: [], // Store namespaces
      namespaceStats: {}, // Store namespace statistics  
      searchQuery: "", // Namespace search
      selectedNamespace: null, // Currently selected namespace
      
      deployments: [], // Deployments in selected namespace
      deploymentSearchQuery: "", // Deployment search

      pods: [], // Pods in selected namespace
      podSearchQuery: "", // Pod search

      // Overview metrics
      totalPods: 0,
      totalDeployments: 0,
      totalServices: 0,

      // Loading states
      loading: {
        namespaces: false,
        deployments: false,
        pods: false,
        yaml: false,
        logs: false,
        scale: false,
        create: false,
        namespaceDetails: false,
        deploymentDetails: false
      },

      // YAML dialog related
      yamlDialogVisible: false,
      yamlContent: "",
      yamlResource: "",
      yamlResourceName: "",

      // Logs dialog related
      logDialogVisible: false,
      selectedPod: null,
      podContainers: ["default"],
      selectedContainer: "default",
      logLines: 100,
      podLogs: "",

      // Scale Deployment dialog related
      scaleDialogVisible: false,
      selectedDeployment: null,
      replicaCount: 1,

      // Create Deployment dialog related
      createDialogVisible: false,
      createTabActive: "form",
      deploymentForm: {
        name: "",
        image: "",
        replicas: 1,
        port: 80,
        yaml: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80`
      },

      // New: Namespace details related
      namespaceDetailsVisible: false,
      namespaceDetails: null,
      
      // New: Deployment details related  
      deploymentDetailsVisible: false,
      deploymentDetails: null
    };
  },
  computed: {
    // Filtered namespace list
    filteredNamespaces() {
      if (!this.searchQuery) return this.namespaces;
      return this.namespaces.filter(ns => 
        ns.name.toLowerCase().includes(this.searchQuery.toLowerCase())
      );
    },
    // Filtered deployments list
    filteredDeployments() {
      if (!this.deploymentSearchQuery) return this.deployments;
      return this.deployments.filter(dep => 
        dep.name.toLowerCase().includes(this.deploymentSearchQuery.toLowerCase())
      );
    },
    // Filtered pods list
    filteredPods() {
      if (!this.podSearchQuery) return this.pods;
      return this.pods.filter(pod => 
        pod.name.toLowerCase().includes(this.podSearchQuery.toLowerCase())
      );
    }
  },
  methods: {
    // Get namespace tag type
    getNamespaceTagType(namespace) {
      // Set different colors for different types of system namespaces
      if (namespace === 'default') return 'primary';
      if (namespace === 'kube-system') return 'danger';
      if (namespace.includes('istio')) return 'warning';
      if (namespace.startsWith('kube-')) return '';
      return 'success'; // User namespaces
    },

    // Get status tag type
    getStatusType(status) {
      if (!status) return 'info';
      status = status.toLowerCase();
      if (status === 'running' || status === 'active') return 'success';
      if (status === 'pending') return 'warning';
      if (status === 'failed' || status === 'error') return 'danger';
      return 'info';
    },

    // Get Pod status tag type
    getPodStatusType(status) {
      if (!status) return 'info';
      status = status.toLowerCase();
      if (status === 'running') return 'success';
      if (status === 'pending') return 'warning';
      if (status === 'succeeded') return 'success';
      if (status === 'failed') return 'danger';
      if (status === 'unknown') return 'info';
      if (status === 'terminating') return 'danger';
      return 'info';
    },

    // Get deployment count for namespace (real implementation)
    getNamespaceDeploymentCount(namespace) {
      return this.namespaceStats[namespace]?.deployments || "";
    },

    // Get pod count for namespace (real implementation)
    getNamespacePodCount(namespace) {
      return this.namespaceStats[namespace]?.pods || "";
    },

    // Fetch namespace statistics
    async fetchNamespaceStatistics() {
      try {
        const response = await this.$http2.get("/api/namespaces/statistics");
        // Convert array to object for easy lookup
        this.namespaceStats = {};
        response.data.statistics.forEach(stat => {
          this.namespaceStats[stat.namespace] = {
            deployments: stat.deployments,
            pods: stat.pods
          };
        });
      } catch (error) {
        console.error("Error fetching namespace statistics:", error);
        // If API doesn't exist yet, fail silently
      }
    },

    // Fetch namespace list
    async fetchNamespaces() {
      this.loading.namespaces = true;
      try {
        const response = await this.$http2.get("/api/namespaces");
        this.namespaces = response.data.namespaces.map((name, index) => ({
          index: index + 1,
          name,
        }));
        
        // Update overview metrics
        await this.updateOverviewMetrics();
        
        // Fetch namespace statistics
        await this.fetchNamespaceStatistics();
        
        // If there was a previously selected namespace, maintain selection
        if (this.selectedNamespace) {
          const found = this.namespaces.find(ns => ns.name === this.selectedNamespace);
          if (!found) {
            this.selectedNamespace = null;
            this.deployments = [];
            this.pods = [];
          }
        }
        
        this.$message.success("Namespace list has been updated");
      } catch (error) {
        console.error("Error fetching namespaces:", error);
        this.$message.error("Failed to fetch namespaces, please try again");
      } finally {
        this.loading.namespaces = false;
      }
    },

    // Update overview metrics
    async updateOverviewMetrics() {
      try {
        // Fetch cluster overview data
        const response = await this.$http2.get("/api/cluster/overview");
        this.totalPods = response.data.resources.pods;
        this.totalDeployments = response.data.resources.deployments;
        this.totalServices = response.data.resources.services;
      } catch (error) {
        console.error("Error fetching overview metrics:", error);
      }
    },

    // Handle namespace click
    async handleNamespaceClick(row) {
      this.selectedNamespace = row.name;
      await this.fetchDeployments(row.name);
    },

    // Fetch deployment list
    async fetchDeployments(namespace) {
      this.loading.deployments = true;
      try {
        const response = await this.$http2.get(`/api/deployments/${namespace}`);
        // Assume backend returns more detailed deployment information
        if (response.data.deploymentDetails) {
          this.deployments = response.data.deploymentDetails;
        } else {
          // Compatible with old API return format, only names
          this.deployments = response.data.deployments.map(deployment => ({
            name: deployment,
            status: "Unknown", // These values should be returned by API in real environment
            currentReplicas: 0,
            desiredReplicas: 0,
            uptime: "Unknown"
          }));
        }

        this.$message.success(`Deployments for namespace ${namespace} have been loaded`);
        } catch (error) {
          console.error("Error fetching deployments:", error);
          this.$message.error("Failed to fetch deployments, please try again");
        } finally {
          this.loading.deployments = false;
        }
    },

    // Fetch Pod list
    async fetchPods() {
      if (!this.selectedNamespace) return;
      
      this.loading.pods = true;
      try {
        const response = await this.$http2.get(`/api/pods/${this.selectedNamespace}`);
        
        // Assume backend returns more detailed pod information
        if (response.data.podDetails) {
          // If backend returns detailed information, but may lack creation_time, need to fetch additionally
          this.pods = await Promise.all(response.data.podDetails.map(async (pod) => {
            try {
              // Get detailed information for each Pod, including creation_time
              const detailResponse = await this.$http2.get(`/api/pod/${this.selectedNamespace}/${pod.name}`);
              return {
                ...pod,
                creation_time: detailResponse.data.creation_time
              };
            } catch (error) {
              console.warn(`Failed to fetch details for pod ${pod.name}:`, error);
              return {
                ...pod,
                creation_time: 'Unknown'
              };
            }
          }));
        } else {
          // Compatible with old API return format, only names
          this.pods = response.data.pods.map(pod => ({
            name: pod,
            status: "Unknown", // These values should be returned by API in real environment
            ip: "N/A",
            node: "N/A",
            restarts: 0,
            age: "Unknown",
            creation_time: "Unknown"
          }));
        }

        this.$message.success(`Pods for namespace ${this.selectedNamespace} have been loaded`);
      } catch (error) {
        console.error("Error fetching pods:", error);
        this.$message.error("Failed to fetch Pods, please try again");
      } finally {
        this.loading.pods = false;
      }
    },

    // View namespace details - show details dialog
    async viewNamespaceDetails(namespace) {
      try {
        // Set loading state
        this.loading.namespaceDetails = true;
        this.namespaceDetailsVisible = true;
        
        // Parallel fetch multiple information of the namespace
        const promises = [
          // 1. Get deployment list for this namespace
          this.$http2.get(`/api/deployments/${namespace.name}`),
          // 2. Get Pod list for this namespace  
          this.$http2.get(`/api/pods/${namespace.name}`),
          // 3. Get namespace YAML
          this.$http2.get(`/api/yaml/namespace/${namespace.name}`)
        ];
        
        const [deploymentsRes, podsRes, yamlRes] = await Promise.all(promises);
        
        // Assemble namespace details data
        this.namespaceDetails = {
          name: namespace.name,
          deployments: deploymentsRes.data.deploymentDetails || [],
          pods: podsRes.data.podDetails || [],
          yaml: yamlRes.data.yaml,
          statistics: {
            deploymentCount: deploymentsRes.data.deploymentDetails?.length || 0,
            podCount: podsRes.data.podDetails?.length || 0
          }
        };
        
      } catch (error) {
        console.error("Error fetching namespace details:", error);
        this.$message.error(`Failed to get namespace details: ${error.response?.data?.detail || error.message}`);
      } finally {
        this.loading.namespaceDetails = false;
      }
    },

    // Handle namespace dropdown menu commands
    handleNamespaceCommand(command, namespace) {
      switch (command) {
        case "view-details":
          this.viewNamespaceDetails(namespace);
          break;
        case "view-yaml":
          this.viewNamespaceYaml(namespace);
          break;
        case "pods":
          this.handleNamespaceClick(namespace);
          this.fetchPods();
          break;
      }
    },

    // View namespace YAML
    async viewNamespaceYaml(namespace) {
      this.yamlDialogVisible = true;
      this.yamlContent = "";
      this.yamlResource = "namespace";
      this.yamlResourceName = namespace.name;
      this.loading.yaml = true;

      try {
        const response = await this.$http2.get(`/api/yaml/namespace/${namespace.name}`);
        this.yamlContent = response.data.yaml;
      } catch (error) {
        console.error("Error fetching namespace YAML:", error);
        this.$message.error("Failed to fetch namespace YAML");
        this.yamlContent = "Error: Unable to get YAML";
      } finally {
        this.loading.yaml = false;
      }
    },

    // View Deployment details - show details dialog
    async viewDeploymentDetails(deployment) {
      try {
        // Set loading state
        this.loading.deploymentDetails = true;
        this.deploymentDetailsVisible = true;
        
        // Get deployment details data
        const promises = [
          // 1. Get Deployment YAML
          this.$http2.get(`/api/yaml/deployment/${this.selectedNamespace}/${deployment.name}`),
          // 2. Get Pods related to this deployment (filter by labels)
          this.$http2.get(`/api/pods/${this.selectedNamespace}`),
        ];
        
        // If there are corresponding Pods, get metrics data
        let metricsPromise = null;
        const pods = await this.$http2.get(`/api/pods/${this.selectedNamespace}`);
        const relatedPods = pods.data.podDetails?.filter(pod => 
          pod.name.startsWith(deployment.name + '-')
        ) || [];
        
        if (relatedPods.length > 0) {
          // Get metrics data for the first Pod as example
          const firstPod = relatedPods[0];
          metricsPromise = this.$http2.get(`/api/all_metrics/${this.selectedNamespace}/${firstPod.name}`);
        }
        
        const [yamlRes] = await Promise.all(promises);
        const metricsRes = metricsPromise ? await metricsPromise : null;
        
        // Assemble deployment details data
        this.deploymentDetails = {
          name: deployment.name,
          namespace: this.selectedNamespace,
          status: deployment.status,
          currentReplicas: deployment.currentReplicas,
          desiredReplicas: deployment.desiredReplicas,
          uptime: deployment.uptime,
          yaml: yamlRes.data.yaml,
          relatedPods: relatedPods,
          metrics: metricsRes?.data || null,
          // Add more useful information
          createdAt: deployment.createdAt,
          labels: deployment.labels || {},
          annotations: deployment.annotations || {}
        };
        
      } catch (error) {
        console.error("Error fetching deployment details:", error);
        this.$message.error(`Failed to get deployment details: ${error.response?.data?.detail || error.message}`);
      } finally {
        this.loading.deploymentDetails = false;
      }
    },

    // View Deployment YAML
    async viewDeploymentYaml(deployment) {
      this.yamlDialogVisible = true;
      this.yamlContent = "";
      this.yamlResource = "deployment";
      this.yamlResourceName = deployment.name;
      this.loading.yaml = true;

      try {
        const response = await this.$http2.get(`/api/yaml/deployment/${this.selectedNamespace}/${deployment.name}`);
        this.yamlContent = response.data.yaml;
      } catch (error) {
        console.error("Error fetching deployment YAML:", error);
        this.$message.error("Failed to fetch deployment YAML");
        this.yamlContent = "Error: Unable to get YAML";
      } finally {
        this.loading.yaml = false;
      }
    },

    // Restart Deployment
    async restartDeployment(deployment) {
      try {
        this.$confirm(`Are you sure you want to restart deployment ${deployment.name}?`, 'Confirm', {
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          type: 'warning'
        }).then(async () => {
          const loading = this.$loading({
            lock: true,
            text: 'Restarting...',
            spinner: 'el-icon-loading',
            background: 'rgba(0, 0, 0, 0.7)'
          });
          
          try {
            await this.$http2.post(`/api/deployment/restart/${this.selectedNamespace}/${deployment.name}`);
            this.$message.success(`Deployment ${deployment.name} restarted successfully`);
            this.fetchDeployments(this.selectedNamespace);
          } catch (error) {
            console.error("Error restarting deployment:", error);
            this.$message.error(`Failed to restart deployment: ${error.response && error.response.data && error.response.data.detail ? error.response.data.detail : error.message}`);
          } finally {
            loading.close();
          }
        }).catch(() => {
          this.$message.info('Restart cancelled');
        });
      } catch (error) {
        console.error("Error in restart confirmation:", error);
      }
    },

    // Scale Deployment
    scaleDeployment(deployment) {
      this.selectedDeployment = deployment;
      this.replicaCount = deployment.desiredReplicas || 1;
      this.scaleDialogVisible = true;
    },

    // Confirm scale
    async confirmScale() {
      if (!this.selectedDeployment) return;
      
      this.loading.scale = true;
      try {
        await this.$http2.post(`/api/deployment/scale/${this.selectedNamespace}/${this.selectedDeployment.name}`, {
          replicas: this.replicaCount
        });
        
        this.$message.success(`Deployment ${this.selectedDeployment.name} replica count has been set to ${this.replicaCount}`);
        this.scaleDialogVisible = false;
        this.fetchDeployments(this.selectedNamespace);
      } catch (error) {
        console.error("Error scaling deployment:", error);
        this.$message.error(`Failed to set replica count: ${error.response && error.response.data && error.response.data.detail ? error.response.data.detail : error.message}`);
      } finally {
        this.loading.scale = false;
      }
    },

    async viewPodYaml(pod) {
      this.yamlDialogVisible = true;
      this.yamlContent = "";
      this.yamlResource = "pod";
      this.yamlResourceName = pod.name;
      this.loading.yaml = true;

      try {
        const response = await this.$http2.get(`/api/yaml/pod/${this.selectedNamespace}/${pod.name}`);
        this.yamlContent = response.data.yaml;
      } catch (error) {
        console.error("Error fetching pod YAML:", error);
        this.$message.error("Failed to fetch Pod YAML");
        this.yamlContent = "Error: Unable to get YAML";
      } finally {
        this.loading.yaml = false;
      }
    },

    // View specific container logs
    async viewContainerLogs(pod, containerName) {
      this.selectedPod = pod;
      this.selectedContainer = containerName;
      this.podContainers = pod.containers || [containerName];
      this.logDialogVisible = true;
      this.podLogs = "";
      this.loading.logs = true;

      try {
        const response = await this.$http2.get(`/api/pod/logs/${this.selectedNamespace}/${pod.name}`, {
          params: {
            container: containerName,
            lines: this.logLines
          }
        });
        
        this.podLogs = response.data.logs;
        
        if (!this.podLogs) {
          this.$message.info("No log data found");
        }
      } catch (error) {
        console.error("Error fetching container logs:", error);
        this.$message.error("Failed to fetch container logs");
        this.podLogs = "Error: Unable to get logs";
      } finally {
        this.loading.logs = false;
      }
    },

    async viewPodLogs(pod) {
      this.selectedPod = pod;
      this.logDialogVisible = true;
      this.podLogs = "";
      this.loading.logs = true;

      try {
        // First get Pod's container list
        const containersResponse = await this.$http2.get(`/api/pod/containers/${this.selectedNamespace}/${pod.name}`);
        this.podContainers = containersResponse.data.containers;
        this.selectedContainer = this.podContainers[0] || "default";
        
        // Then get default container logs
        await this.refreshLogs();
      } catch (error) {
        console.error("Error fetching pod containers:", error);
        this.$message.error("Failed to fetch Pod container list");
        this.loading.logs = false;
      }
    },

    // Refresh logs
    async refreshLogs() {
      if (!this.selectedPod) return;
      
      this.loading.logs = true;
      try {
        const response = await this.$http2.get(`/api/pod/logs/${this.selectedNamespace}/${this.selectedPod.name}`, {
          params: {
            container: this.selectedContainer,
            lines: this.logLines
          }
        });
        
        this.podLogs = response.data.logs;
        
        if (!this.podLogs) {
          this.$message.info("No log data found");
        }
      } catch (error) {
        console.error("Error fetching pod logs:", error);
        this.$message.error("Failed to fetch Pod logs");
        this.podLogs = "Error: Unable to get logs";
      } finally {
        this.loading.logs = false;
      }
    },

    // Download logs
    downloadLogs() {
      if (!this.podLogs) return;
      
      const blob = new Blob([this.podLogs], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `${this.selectedPod.name}-${this.selectedContainer}.log`;
      
      document.body.appendChild(a);
      a.click();
      
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },

    // Delete Pod
    async deletePod(pod) {
      try {
        await this.$confirm(`Are you sure you want to delete Pod ${pod.name}?`, 'Warning', {
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          type: 'warning'
        }).then(async () => {
          const loading = this.$loading({
            lock: true,
            text: 'Deleting...',
            spinner: 'el-icon-loading',
            background: 'rgba(0, 0, 0, 0.7)'
          });
          
          try {
            await this.$http2.delete(`/api/pod/${this.selectedNamespace}/${pod.name}`);
            this.$message.success(`Pod ${pod.name} deleted successfully`);
            this.fetchPods();
          } catch (error) {
            console.error("Error deleting pod:", error);
            this.$message.error(`Failed to delete Pod: ${error.response && error.response.data && error.response.data.detail ? error.response.data.detail : error.message}`);
          } finally {
            loading.close();
          }
        }).catch(() => {
          this.$message.info('Delete operation cancelled');
        });
      } catch (error) {
        console.error("Error in delete confirmation:", error);
      }
    },

    // Format creation time - Learn from ServiceDetail.vue time handling approach
    formatCreationTime(creationTime) {
      if (!creationTime || creationTime === 'Unknown') {
        return 'Unknown';
      }
      
      try {
        // If it's timestamp format, convert to readable format
        const date = new Date(creationTime);
        if (isNaN(date.getTime())) {
          return creationTime; // If cannot parse, return original value
        }
        
        // Return format: MM-DD HH:mm
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${month}-${day} ${hours}:${minutes}`;
      } catch (error) {
        return creationTime; // Return original value when error occurs
      }
    },

    // Copy YAML
    copyYaml() {
      if (!this.yamlContent) return;
      
      const textArea = document.createElement('textarea');
      textArea.value = this.yamlContent;
      document.body.appendChild(textArea);
      textArea.select();
      
      try {
        document.execCommand('copy');
        this.$message.success('YAML copied to clipboard successfully');
      } catch (err) {
        console.error('Could not copy text: ', err);
        this.$message.error('Copy failed, please copy manually');
      }
      
      document.body.removeChild(textArea);
    },

    // Create Deployment
    createDeployment() {
      // Reset form
      this.deploymentForm = {
        name: "",
        image: "",
        replicas: 1,
        port: 80,
        yaml: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
  namespace: ${this.selectedNamespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80`
      };
      
      this.createDialogVisible = true;
      this.createTabActive = "form";
    },

    // Confirm create Deployment
    async confirmCreateDeployment() {
      this.loading.create = true;
      
      try {
        let payload;
        
        if (this.createTabActive === "form") {
          // Create from form
          payload = {
            name: this.deploymentForm.name,
            image: this.deploymentForm.image,
            replicas: this.deploymentForm.replicas,
            port: this.deploymentForm.port
          };
          
          await this.$http2.post(`/api/deployment/create/${this.selectedNamespace}`, payload);
        } else {
          // Create from YAML
          payload = {
            yaml: this.deploymentForm.yaml
          };
          
          await this.$http2.post(`/api/deployment/create-from-yaml/${this.selectedNamespace}`, payload);
        }
        
        this.$message.success("Deployment created successfully");
        this.createDialogVisible = false;
        this.fetchDeployments(this.selectedNamespace);
      } catch (error) {
        console.error("Error creating deployment:", error);
        this.$message.error(`Failed to create Deployment: ${error.response && error.response.data && error.response.data.detail ? error.response.data.detail : error.message}`);
      } finally {
        this.loading.create = false;
      }
    },
  },
  mounted() {
    // Automatically fetch namespace list when page loads
    this.fetchNamespaces();
  }
};
</script>

<style scoped>
/* Global container */
.kubernetes-dashboard {
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: calc(100vh - 60px);
}

/* Overview dashboard */
.overview-dashboard {
  margin-bottom: 30px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.metric-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.metric-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.15);
}

.namespaces-card::before { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); }
.pods-card::before { background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%); }
.deployments-card::before { background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); }
.services-card::before { background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%); }

.metric-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.pods-card .metric-icon { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.deployments-card .metric-icon { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.services-card .metric-icon { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }

.metric-content {
  flex: 1;
  margin: 0 20px;
}

.metric-value {
  font-size: 32px;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 14px;
  color: #7f8c8d;
  font-weight: 500;
}


.trend-indicator.positive { color: #27ae60; }
.trend-indicator.stable { color: #f39c12; }

/* Section containers */
.namespace-section,
.deployments-section,
.pods-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}

/* Section headers */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f8f9fa;
}

.section-title h2 {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 8px 0;
}

.section-subtitle {
  font-size: 14px;
  color: #7f8c8d;
  margin: 0;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  width: 220px;
}

.refresh-btn, .create-btn {
  border-radius: 8px;
  font-weight: 500;
}

/* Namespace grid */
.namespaces-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.namespace-card {
  width: 350px;
  height: 140px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 10px 10px 20px 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.namespace-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.namespace-card:hover::before,
.namespace-card.selected::before {
  transform: scaleX(1);
}

.namespace-card:hover {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
}

.namespace-card.selected {
  border-color: #667eea;
  background: linear-gradient(135deg, #667eea08 0%, #764ba208 100%);
}

.namespace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.namespace-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.namespace-tag {
  font-weight: 650;
}

.namespace-index {
  font-size: 12px;
  color: #95a5a6;
  font-weight: 500;
}

.namespace-menu {
  color: #7f8c8d;
  padding: 4px;
}

.namespace-stats {
  margin-bottom: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #5a6c7d;
}

.stat-item i {
  color: #667eea;
}

.namespace-status {
  margin-top: -8px;
  margin-right: 2px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #27ae60;
}

.status-text {
  font-size: 12px;
  color: #27ae60;
  font-weight: 500;
}

/* Deployment container - Fix empty state centering issue */
.deployments-container {
  margin-bottom: 20px;
}

.deployments-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.deployment-card {
  width: 220px;
  padding: 0;
  transition: all 0.3s;
  cursor: pointer;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.deployment-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.deployment-header {
  padding: 15px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.deployment-title {
  margin: 0;
  font-size: 14px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.status-tag {
  margin-left: 5px;
}

.deployment-info {
  padding: 10px 15px;
}

.info-item {
  display: flex;
  align-items: center;
  font-size: 12px;
  margin-bottom: 5px;
  color: #606266;
}

.info-item i {
  margin-right: 5px;
  font-size: 14px;
}

.deployment-actions {
  display: flex;
  justify-content: space-around;
  border-top: 1px solid #ebeef5;
  padding: 8px 0;
}

/* Pod table - Fix column width issue */
.modern-table-container {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e9ecef;
  overflow-x: auto;
}

.modern-table {
  border-radius: 12px;
  width: 100%;
  min-width: 1150px; /* Increase minimum width to accommodate new Creation Time column */
  font-size: 15px; /* Enlarge Pod list font */
}

.modern-table .el-table__header {
  background: #f8f9fa;
  font-size: 16px; /* Enlarge header font */
}

.modern-table .el-table__header th {
  background: #f8f9fa;
  color: #5a6c7d;
  font-weight: 600;
  border: none;
  font-size: 16px; /* Enlarge header font */
}

.modern-table .el-table__body tr:hover {
  background: #f8f9fa;
}

.modern-table .el-table__body td {
  font-size: 15px; /* Enlarge table content font */
}

.pod-link {
  color: #4facfe;
  text-decoration: none;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: color 0.2s ease;
}

.pod-link:hover {
  color: #2c3e50;
  text-decoration: underline;
}

.pod-name-text {
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
}

.restart-count.high-restarts {
  color: #e74c3c;
  font-weight: 600;
}

.creation-time {
  color: #606266;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

.table-actions {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: nowrap;
  justify-content: flex-start;
  width: 100%;
  min-width: 180px;
}

.table-action-btn {
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
  white-space: nowrap;
  flex-shrink: 0;
}

.table-action-btn:hover {
  background: #f8f9fa;
}

.table-action-btn.danger:hover {
  color: #e74c3c;
  background: #fdf2f2;
}

/* Details dialog styles */
.details-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background-color: #fafafa;
}

.details-section h3 {
  margin: 0 0 15px 0;
  color: #303133;
}

.info-item {
  margin-bottom: 8px;
  font-size: 14px;
}

.info-item strong {
  color: #606266;
  margin-right: 8px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.metric-card {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  text-align: center;
  background-color: #fff;
}

.metric-card h4 {
  margin: 0 0 8px 0;
  color: #606266;
  font-size: 14px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #7f8c8d;
  width: 100%;
}

.empty-illustration {
  font-size: 64px;
  color: #bdc3c7;
  margin-bottom: 16px;
}

.empty-state h3 {
  font-size: 18px;
  color: #5a6c7d;
  margin: 0 0 8px 0;
}

.empty-state p {
  font-size: 14px;
  margin: 0 0 20px 0;
}

.empty-action-btn {
  border-radius: 8px;
}

/* Other buttons */
.pods-action {
  margin-top: 24px;
  text-align: center;
}

.view-pods-btn {
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: 500;
}

.namespace-highlight {
  font-weight: 600;
  margin: 0 8px;
}

/* Dialog styles */
.yaml-content, .log-content {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  overflow: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  max-height: 60vh;
  white-space: pre-wrap;
  line-height: 1.5;
}

/* Responsive design */
@media (max-width: 768px) {
  .kubernetes-dashboard {
    padding: 12px;
  }
  
  .overview-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .section-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .search-input {
    width: 100%;
  }
  
  .namespaces-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .deployments-list {
    flex-direction: column;
    gap: 12px;
  }
  
  .deployment-card {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .metric-card {
    padding: 16px;
  }
  
  .metric-icon {
    width: 48px;
    height: 48px;
    font-size: 20px;
  }
  
  .metric-value {
    font-size: 24px;
  }
  
  .deployment-card {
    width: 100%;
  }
  
  .table-actions {
    flex-direction: column;
    gap: 2px;
  }
}
</style>