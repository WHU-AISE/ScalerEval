<template>
    <div class="header-container">
        <div class="le-context">
            <el-button icon="el-icon-menu" size="medium" @click="handleMenu"></el-button>

            <el-breadcrumb separator="/" style="padding-left:20px;">
                <el-breadcrumb-item 
                    v-for="(item, index) in tags" 
                    :key="item.path"
                    :class="{ 'is-active': $route.path === item.path }"
                >
                    {{ item.label }}
                </el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="ri-context">
            <span class="user-info">
                <i class="el-icon-user" style="font-size: 15px; color: white;"></i>
                <span style="margin-left: 8px; color: white;">Kubernetes</span>
            </span>
        </div>
    </div>
</template>

<script>
import { mapState } from "vuex";

export default {
    name: 'Header',
    data() {
        return {}
    },
    methods: {
        handleMenu() {
            this.$store.commit('collapseChange');
        }
    },
    computed: {
        ...mapState({
            tags: state => state.tab?.tabsList || []
        })
    }
}
</script>

<style lang="less" scoped>
.header-container {
    margin-top: -25px;
    margin-left: 20px;
    margin-right: 40px;
    border-radius: 10px 10px 0 0;
    height: 60px;
    background-color: #3A4084;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .le-context {
        margin-left: 20px;
        display: flex;
        align-items: center;

        /deep/.el-breadcrumb__item {
            .el-breadcrumb__inner {
                font-weight: normal;
                cursor: default;
                color: #bbb; // 默认颜色稍微暗一点
                
                &.is-link {
                    color: #ffffff;
                }
            }

            &:last-child {
                .el-breadcrumb__inner {
                    color: #ffffff;
                }
            }
            
            // 添加激活状态样式
            &.is-active {
                .el-breadcrumb__inner {
                    color: #ffffff !important;
                    font-weight: bold;
                }
            }
        }
    }

    .ri-context {
        padding-right: 17px;

        .user-info {
            display: flex;
            align-items: center;
            cursor: pointer;
        }
    }
}
</style>