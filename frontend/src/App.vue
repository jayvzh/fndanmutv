<template>
  <v-app>
    <div class="app-root">
      <component
        :is="currentComponent"
        :authed="authed"
        @switch="switchComponent"
        @login="handleLogin"
        @logout="handleLogout"
      ></component>
    </div>

    <!-- 全局通知：刮削完成等，跨页面悬浮右下角 -->
    <v-snackbar
      v-model="notify.visible"
      :color="notify.color"
      :timeout="6000"
      location="bottom right"
      rounded="lg"
      elevation="8"
    >
      <div class="d-flex align-center">
        <v-icon :icon="notify.icon" class="mr-3" size="22"></v-icon>
        <div>
          <div class="font-weight-medium">{{ notify.title }}</div>
          <div v-if="notify.text" class="text-body-2">{{ notify.text }}</div>
        </div>
      </div>
      <template #actions>
        <v-btn variant="text" @click="notify.visible = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, reactive, shallowRef, onMounted, onBeforeUnmount } from 'vue';
import Page from './components/Page.vue';
import Config from './components/Config.vue';

const TOKEN_KEY = 'danmutv_token';

const authed = ref(!!localStorage.getItem(TOKEN_KEY));
const currentComponent = shallowRef(Page);

const switchComponent = () => {
  currentComponent.value = currentComponent.value === Page ? Config : Page;
};

const handleLogin = (token) => {
  localStorage.setItem(TOKEN_KEY, token);
  authed.value = true;
};

const handleLogout = () => {
  localStorage.removeItem(TOKEN_KEY);
  authed.value = false;
  if (currentComponent.value === Config) {
    currentComponent.value = Page;
  }
};

const handleUnauthorized = () => {
  handleLogout();
};

// ── 全局通知 ──
const notify = reactive({
  visible: false,
  color: 'success',
  icon: 'mdi-check-circle',
  title: '',
  text: '',
});

const showNotify = (e) => {
  const detail = e.detail || {};
  const success = detail.success !== false;
  notify.color = success ? 'success' : 'error';
  notify.icon = success ? 'mdi-check-circle' : 'mdi-alert-circle';
  notify.title = detail.title || (success ? '刮削完成' : '刮削失败');
  notify.text = detail.text || '';
  notify.visible = true;
};

onMounted(() => {
  window.addEventListener('auth:unauthorized', handleUnauthorized);
  window.addEventListener('app:notify', showNotify);
});

onBeforeUnmount(() => {
  window.removeEventListener('auth:unauthorized', handleUnauthorized);
  window.removeEventListener('app:notify', showNotify);
});
</script>

<style>
.app-root {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #F5F7FA;
}

.v-btn {
  text-transform: none !important;
}
</style>
