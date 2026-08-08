<template>
  <div class="plugin-page">
    <v-card flat class="rounded border">
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2 bg-primary-lighten-5">
        <v-icon icon="mdi-video" class="mr-2" color="primary" size="small" />
        <span>影视弹幕刮削</span>
      </v-card-title>
      
      <v-tabs
        v-model="activeTab"
        class="px-3"
        centered
        background-color="transparent"
        shrink
      >
        <v-tab value="dashboard">
          <v-icon icon="mdi-view-dashboard" size="small" class="mr-1"></v-icon>
          仪表盘
        </v-tab>
        <v-tab value="browse">
          <v-icon icon="mdi-folder" size="small" class="mr-1"></v-icon>
          目录浏览
        </v-tab>
        <v-tab value="retry">
          <v-icon icon="mdi-alert-circle-outline" size="small" class="mr-1"></v-icon>
          重试任务
        </v-tab>
        <v-tab value="history">
          <v-icon icon="mdi-history" size="small" class="mr-1"></v-icon>
          历史记录
        </v-tab>
        <v-tab value="cleanup">
          <v-icon icon="mdi-delete-sweep" size="small" class="mr-1"></v-icon>
          清理
        </v-tab>
      </v-tabs>

      <v-card-text class="p-0">
        <Dashboard v-if="activeTab === 'dashboard'" :api="api" />
        <BrowseView v-else-if="activeTab === 'browse'" :api="api" @refresh="refreshDashboard" />
        <RetryTasks v-else-if="activeTab === 'retry'" :api="api" />
        <History v-else-if="activeTab === 'history'" :api="api" />
        <Cleanup v-else-if="activeTab === 'cleanup'" :api="api" />
      </v-card-text>

      <v-divider></v-divider>
      
      <v-card-actions class="px-2 py-1">
        <v-btn color="info" @click="emit('switch')" prepend-icon="mdi-cog" variant="text" size="small">配置</v-btn>
        <v-spacer></v-spacer>
        <v-btn color="grey" @click="emit('close')" prepend-icon="mdi-close" variant="text" size="small">关闭</v-btn>
      </v-card-actions>
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

const props = defineProps({
  api: { 
    type: [Object, Function],
    required: true,
  }
});

const emit = defineEmits(['close', 'switch']);

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
  max-width: 80rem;
  margin: 0 auto;
  padding: 0.5rem;
}

.bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.07);
}

.border {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
