<template>
  <div class="plugin-page">
    <v-card flat class="main-card rounded-lg overflow-hidden">
      <!-- 顶部紧凑工具栏：标题 + 登录/配置 -->
      <div class="topbar d-flex align-center px-5 py-3">
        <v-icon icon="mdi-television-play" color="primary" size="26" class="mr-3" />
        <div class="topbar-title">DanmuTV</div>
        <v-spacer></v-spacer>

        <!-- 已登录：显示配置 + 登出 -->
        <template v-if="authed">
          <v-btn
            color="primary"
            variant="tonal"
            @click="emit('switch')"
            prepend-icon="mdi-cog"
            size="small"
            class="mr-2"
          >
            配置
          </v-btn>
          <v-btn
            color="grey"
            variant="text"
            @click="emit('logout')"
            prepend-icon="mdi-logout"
            size="small"
          >
            登出
          </v-btn>
        </template>
        <!-- 未登录：显示登录按钮 -->
        <v-btn
          v-else
          color="primary"
          variant="tonal"
          @click="loginDialog = true"
          prepend-icon="mdi-login"
          size="small"
        >
          登录
        </v-btn>
      </div>

      <v-divider></v-divider>

      <!-- 标签栏：未登录时只显示仪表盘 -->
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
        <v-tab v-if="authed" value="browse" class="tab-item">
          <v-icon icon="mdi-folder" size="18" class="mr-2"></v-icon>
          目录浏览
        </v-tab>
        <v-tab v-if="authed" value="retry" class="tab-item">
          <v-icon icon="mdi-alert-circle-outline" size="18" class="mr-2"></v-icon>
          重试任务
        </v-tab>
        <v-tab v-if="authed" value="history" class="tab-item">
          <v-icon icon="mdi-history" size="18" class="mr-2"></v-icon>
          历史记录
        </v-tab>
        <v-tab v-if="authed" value="cleanup" class="tab-item">
          <v-icon icon="mdi-delete-sweep" size="18" class="mr-2"></v-icon>
          清理
        </v-tab>
      </v-tabs>

      <v-divider></v-divider>

      <v-card-text class="pa-6">
        <Dashboard v-if="activeTab === 'dashboard'" />
        <BrowseView v-else-if="activeTab === 'browse' && authed" @refresh="refreshDashboard" />
        <RetryTasks v-else-if="activeTab === 'retry' && authed" />
        <History v-else-if="activeTab === 'history' && authed" />
        <Cleanup v-else-if="activeTab === 'cleanup' && authed" />
      </v-card-text>
    </v-card>

    <!-- 登录对话框 -->
    <v-dialog v-model="loginDialog" max-width="400">
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center justify-center pt-5 pb-2">
          <v-icon icon="mdi-lock" color="primary" size="28" class="mr-2" />
          <span class="text-h6">管理员登录</span>
        </v-card-title>
        <v-card-text class="px-6 pb-2">
          <v-alert v-if="loginError" type="error" variant="tonal" class="mb-4" closable @click:close="loginError = ''">
            {{ loginError }}
          </v-alert>
          <v-text-field
            v-model="inputPassword"
            label="访问密码"
            type="password"
            variant="outlined"
            autocomplete="current-password"
            @keyup.enter="doLogin"
            :disabled="verifying"
            autofocus
            density="comfortable"
          />
        </v-card-text>
        <v-card-actions class="px-6 pb-6">
          <v-spacer />
          <v-btn color="grey" variant="text" @click="loginDialog = false">取消</v-btn>
          <v-btn
            color="primary"
            :loading="verifying"
            :disabled="!inputPassword.trim()"
            @click="doLogin"
            prepend-icon="mdi-login"
          >
            登录
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import Dashboard from './Dashboard.vue';
import BrowseView from './BrowseView.vue';
import RetryTasks from './RetryTasks.vue';
import History from './History.vue';
import Cleanup from './Cleanup.vue';
import { axiosInstance } from '../api';

const props = defineProps({
  authed: { type: Boolean, default: false },
});
const emit = defineEmits(['switch', 'login', 'logout']);

const activeTab = ref('dashboard');
const loginDialog = ref(false);
const inputPassword = ref('');
const loginError = ref('');
const verifying = ref(false);

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

// 登出后重置到仪表盘
watch(() => props.authed, (val) => {
  if (!val) {
    activeTab.value = 'dashboard';
  }
});

const doLogin = async () => {
  const password = inputPassword.value.trim();
  if (!password) return;
  verifying.value = true;
  loginError.value = '';
  try {
    // 用密码直接作为 Bearer token 验证，不提前写入 localStorage
    await axiosInstance.get('/auth/verify', {
      headers: { Authorization: `Bearer ${password}` },
    });
    emit('login', password);
    loginDialog.value = false;
    inputPassword.value = '';
  } catch (err) {
    const status = err?.response?.status;
    if (status === 401 || status === 403) {
      loginError.value = '密码错误，请重新输入';
    } else {
      loginError.value = err?.response?.data?.detail || err?.message || '验证失败，请检查后端服务';
    }
  } finally {
    verifying.value = false;
  }
};
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
