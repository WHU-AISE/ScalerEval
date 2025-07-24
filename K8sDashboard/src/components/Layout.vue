<template>
  <div class="layout-container">
    <el-container>
      <el-aside width="auto">
        <AsideMenu />
      </el-aside>
      
      <el-container>
        <el-header class="top-header">
          <Top />
        </el-header>
        
        <el-header class="main-header">
          <Header />
        </el-header>
        
        <div class="header-tab">
          <HeaderTab />
        </div>
        
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
import AsideMenu from './AsideMenu.vue'
import Header from './Header.vue'
import HeaderTab from './HeaderTab.vue'
import Top from './Top.vue'

export default {
  name: 'Layout',
  components: {
    AsideMenu,
    Header,
    HeaderTab,
    Top
  }
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.el-header {
  padding: 0;
}

.top-header {
  height: 145px;
}

.main-header {
  height: 60px;
}

.header-tab {
  height: auto;
}

.el-main {
  margin-left: -15px;
  background-color: rgb(254, 248, 248);
  margin-top: 15px;
  border-radius: 10px;
  width: 100%;
}
</style>