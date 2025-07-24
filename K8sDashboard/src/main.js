// src/main.js
import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

// Element UI
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'

// axios
import axios from 'axios'

Vue.config.productionTip = false

// 创建 axios 实例，配置后端地址
// const axiosInstance1 = axios.create({
//   baseURL: 'http://localhost:8086/jishe' // 如果需要的话
// });

const axiosInstance2 = axios.create({
  baseURL: 'http://127.0.0.1:10001' // 这是关键！你的Kubernetes API后端地址
});

// 使用 Element UI
Vue.use(ElementUI)

// 配置 axios
// Vue.prototype.$http = axiosInstance1
Vue.prototype.$http2 = axiosInstance2 // 确保这里用的是配置了baseURL的实例

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')