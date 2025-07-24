<template>
    <div class="asideContianer">
        <el-menu 
            default-active="KubernetesDashboard"
            class="el-menu-vertical-demo"
            @open="handleOpen"
            @close="handleClose"
            :collapse="isCollapse"
            background-color="#ffffff"
            text-color="#000000"
            active-text-color="#ffd04b"
        >
            <h3 style="white-space: pre">{{ isCollapse ? 'SE':' ScalerEval ' }}</h3>
            
            <el-menu-item
                v-for="item in noChildren"
                :key="item.name"
                :index="item.name"
                @click="clickMenu(item)"
            >
                <i :class="`el-icon-${item.icon}`"></i>
                <span slot="title">{{ item.label }}</span>
            </el-menu-item>

            <el-submenu
                v-for="item in hasChildren"
                :key="item.name"
                :index="item.name"
            >
                <template slot="title">
                    <i :class="`el-icon-${item.icon}`"></i>
                    <span slot="title">{{ item.label }}</span>
                </template>
                <el-menu-item-group
                    v-for="subItem in item.children"
                    :key="subItem.name"
                >
                    <el-menu-item :index="subItem.name" @click="clickMenu(subItem)">
                        {{ subItem.label }}
                    </el-menu-item>
                </el-menu-item-group>
            </el-submenu>
        </el-menu>
    </div>
</template>

<script>
export default {
    name: 'AsideMenu',
    data() {
        return {
            menuData: [
            {
                path: '/KubernetesDashboard',
                name: 'KubernetesDashboard',
                label: 'Kubernetes Dashboard',
                icon: 's-grid',
                url: 'KubernetesDashboard/KubernetesDashboard'
            },
            {
                path: '/ElasticScaling',
                name: 'ElasticScaling',
                label: 'ElasticScaling',
                icon: 's-operation',
                url: 'ElasticScaling/ElasticScaling'
            }
            ],
        };
    },
    methods: {
        handleOpen(key, keyPath) {
            console.log(key, keyPath);
        },
        handleClose(key, keyPath) {
            console.log(key, keyPath);
        },
        clickMenu(item) {
            if(this.$route.path !== item.path && !(this.$route.path === '/Perpage' && item.path === '/')){
                this.$router.push(item.path);
            }

            this.$store.commit('menuChange', item);
        }
    },
    computed: {
        hasChildren() {
            return this.menuData.filter((item) => item.children);
        }, 
        noChildren() {
            return this.menuData.filter((item) => !item.children);
        },
        isCollapse(){
            return this.$store.state.tab?.isCollapse || false;
        }
    },
};
</script>

<style lang="less" scoped>
.el-menu {
    border-radius: 10px;
    box-shadow: 0 15px 35px rgba(0,0,0,0.2);
    margin-left: 55px;
    margin-right: 30px;
    margin-top: 80px;
    height: 100vh;
    border-right: none;
    padding: 0 auto;
    
    h3 {
        color: #edbe3f;
        margin-top: 40px;
        text-align: center;
        line-height: 40px;
        font-size: 30px;
        font-weight: 400;
        padding: 0 auto;
    }
}

.el-menu-vertical-demo:not(.el-menu--collapse) {
    width: 240px;
    min-height: 400px;
}
</style>