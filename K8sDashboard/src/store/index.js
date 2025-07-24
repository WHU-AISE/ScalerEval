import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    tab: {
      isCollapse: false,
      tabsList: [
        {
          path: '/KubernetesDashboard',
          name: 'KubernetesDashboard',
          label: 'Kubernetes Dashboard'
        }
      ]
    }
  },
  mutations: {
    // 切换菜单折叠状态
    collapseChange (state) {
      state.tab.isCollapse = !state.tab.isCollapse
    },

    // 菜单变化，添加tab
    menuChange (state, item) {
      const exists = state.tab.tabsList.find(tab => tab.name === item.name)
      if (!exists) {
        state.tab.tabsList.push(item)
      }
    },

    // Closetab
    closeTag (state, item) {
      const index = state.tab.tabsList.findIndex(tab => tab.name === item.name)
      if (index > -1) {
        state.tab.tabsList.splice(index, 1)
      }
    }
  },
  actions: {
  },
  modules: {
  }
})
