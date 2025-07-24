<template>
  <div class="tabs">
    <el-tag v-for="(item, index) in tags" :key="item.path" :effect="$route.name === item.name ? 'dark' : 'plain'"
      @click="changeMenu(item)" :closable="item.name !== 'KubernetesDashboard'" @close="handleClose(item, index)">
      {{ item.label }}
    </el-tag>
  </div>
</template>

<script>
import { mapState, mapMutations } from "vuex";

export default {
  name: "HeaderTab",
  data() {
    return {};
  },
  computed: {
    ...mapState({
      tags: (state) => state.tab?.tabsList || [],
    }),
  },
  methods: {
    ...mapMutations(['closeTag']),
    changeMenu(item) {
      if (this.$route.path !== item.path) {
        this.$router.push(item.path);
      }
    },
    handleClose(item, index) {
      this.closeTag(item);
      if (this.$route.name !== item.name) {
        return;
      }
      if (this.tags[index - 1]) {
        this.$router.push(this.tags[index - 1].path);
      }
    }
  }
};
</script>

<style lang="less" scoped>
.tabs {
  position: relative;
  z-index: 99;
  opacity: 0.89;
  margin-top: -25px;
  border-radius: 8px 8px 8px 8px;
  margin-left: 25px;
  margin-right: 50px;
  overflow: hidden;
  background: #fff;
  padding-bottom: 7px;
  padding-top: 7px;
  padding-left: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

  .el-tag {
    margin-right: 15px;
    cursor: pointer;
  }
}
</style>