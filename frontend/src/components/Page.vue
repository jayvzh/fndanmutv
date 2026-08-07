<template>
  <div class="plugin-page">
    <v-card flat class="main-card rounded-lg overflow-hidden">
      <!-- 顶部紧凑工具栏：标题 + 配置按钮 -->
      <div class="topbar d-flex align-center px-5 py-3">
        <v-icon icon="mdi-television-play" color="primary" size="26" class="mr-3" />
        <div class="topbar-title">DanmuTV</div>
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          variant="tonal"
          @click="emit('switch')"
          prepend-icon="mdi-cog"
          size="small"
        >
          配置
        </v-btn>
      </div>

      <v-divider></v-divider>

      <!-- 标签栏 -->
      <v-tabs
        v-model="activeTab"
        color="primary"
        bg-color="surface"
        grow
        slider-color="primary"
        class="main-tabs"
      >
        <v-tab value="dashboard" class="tab-item">
          <v-icon icon="mdi-view-dashboard" size="18" class="mr-2"></v-icon>
          仪表盘
        </v-tab>
        <v-tab value="browse" class="tab-item">
          <v-icon icon="mdi-folder" size="18" class="mr-2"></v-icon>
          目录浏览
        </v-tab>
        <v-tab value="retry" class="tab-item">
          <v-icon icon="mdi-alert-circle-outline" size="18" class="mr-2"></v-icon>
          重试任务
        </v-tab>
        <v-tab value="history" class="tab-item">
          <v-icon icon="mdi-history" size="18" class="mr-2"></v-icon>
          历史记录
        </v-tab>
        <v-tab value="cleanup" class="tab-item">
          <v-icon icon="mdi-delete-sweep" size="18" class="mr-2"></v-icon>
          清理
        </v-tab>
      </v-tabs>

      <v-divider></v-divider>

      <v-card-text class="pa-6">
        <Dashboard v-if="activeTab === 'dashboard'" />
        <BrowseView v-else-if="activeTab === 'browse'" @refresh="refreshDashboard" />
        <RetryTasks v-else-if="activeTab === 'retry'" />
        <History v-else-if="activeTab === 'history'" />
        <Cleanup v-else-if="activeTab === 'cleanup'" />
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import Dashboard from './Dashboard.vue';
import BrowseView from './BrowseView.vue';
import RetryTasks from './RetryTasks.vue';
import History from './History.vue';
import Cleanup from './Cleanup.vue';

const emit = defineEmits(['switch']);

const activeTab = ref('dashboard');

const refreshDashboard = () => {
  if (activeTab.value === 'dashboard') {
    window.dispatchEvent(new Event('dashboard-refresh'));
  }
};

watch(activeTab, (newTab) => {
  if (newTab === 'dashboard') {
    refreshDashboard();
  }
});
</script>

<style scoped>
.plugin-page {
  max-width: 90rem;
  width: 100%;
  margin: 0 auto;
  padding: 1.25rem;
  box-sizing: border-box;
}

.main-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
  background: #FFFFFF;
}

.topbar {
  background: #FFFFFF;
}

.topbar-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.87);
  letter-spacing: 0.2px;
}

.main-tabs {
  font-size: 0.95rem;
}

.tab-item {
  font-size: 0.9rem;
  font-weight: 500;
  min-height: 46px;
  text-transform: none;
  letter-spacing: normal;
}
</style>
