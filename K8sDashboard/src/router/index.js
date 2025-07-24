import Vue from 'vue'
import VueRouter from 'vue-router'
import Layout from '@/components/Layout.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/KubernetesDashboard',
    children: [
      {
        path: 'KubernetesDashboard',
        name: 'KubernetesDashboard',
        component: () => import('@/views/KubernetesDashboard.vue'),
        meta: {
          title: 'Kubernetes Dashboard'
        }
      },
      {
        path: 'ElasticScaling',
        name: 'ElasticScaling',
        component: () => import('@/views/ElasticScaling.vue'),
        meta: {
          title: 'ElasticScaling'
        }
      },
      {
        path: 'ServiceDetail/:namespace/:serviceName',
        name: 'ServiceDetail',
        component: () => import('@/views/ServiceDetail.vue'),
        props: true,
        meta: {
          title: 'Pods Details'
        }
      }
    ]
  }
]

const router = new VueRouter({
  routes
})

export default router