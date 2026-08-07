<template>
  <v-app>
    <div class="app-root">
      <v-card v-if="!token" class="login-card" elevation="8">
        <v-card-title class="d-flex align-center justify-center pb-1">
          <v-icon icon="mdi-lock" color="primary" class="mr-2" />
          DanmuTV 访问令牌
        </v-card-title>
        <v-card-text>
          <v-alert v-if="loginError" type="error" density="compact" variant="tonal" class="mb-3">
            {{ loginError }}
          </v-alert>
          <v-text-field
            v-model="inputToken"
            label="访问令牌"
            type="password"
            variant="outlined"
            density="compact"
            autocomplete="current-password"
            @keyup.enter="handleLogin"
            :disabled="verifying"
            autofocus
          />
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-spacer />
          <v-btn
            color="primary"
            :loading="verifying"
            :disabled="!inputToken.trim()"
            @click="handleLogin"
            prepend-icon="mdi-login"
          >
            确认
          </v-btn>
        </v-card-actions>
      </v-card>

      <component
        v-else
        :is="currentComponent"
        @switch="switchComponent"
      ></component>
    </div>
  </v-app>
</template>

<script setup>
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue';
import Page from './components/Page.vue';
import Config from './components/Config.vue';
import api from './api';

const TOKEN_KEY = 'danmutv_token';

const token = ref(localStorage.getItem(TOKEN_KEY) || '');
const inputToken = ref('');
const verifying = ref(false);
const loginError = ref('');

const currentComponent = shallowRef(Page);

const switchComponent = () => {
  currentComponent.value = currentComponent.value === Page ? Config : Page;
};

const handleUnauthorized = () => {
  token.value = '';
  inputToken.value = '';
  currentComponent.value = Page;
};

const handleLogin = async () => {
  const next = inputToken.value.trim();
  if (!next) return;
  verifying.value = true;
  loginError.value = '';
  try {
    localStorage.setItem(TOKEN_KEY, next);
    await api.get('/auth/verify');
    token.value = next;
  } catch (err) {
    localStorage.removeItem(TOKEN_KEY);
    const status = err?.response?.status;
    if (status === 401 || status === 403) {
      loginError.value = '访问令牌无效，请重新输入';
    } else {
      loginError.value = err?.response?.data?.detail || err?.message || '验证失败，请检查后端服务';
    }
  } finally {
    verifying.value = false;
  }
};

onMounted(() => {
  window.addEventListener('auth:unauthorized', handleUnauthorized);
});

onBeforeUnmount(() => {
  window.removeEventListener('auth:unauthorized', handleUnauthorized);
});
</script>

<style>
.app-root {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.login-card {
  max-width: 26rem;
  width: calc(100% - 2rem);
  margin: auto;
  border-radius: 12px;
}
</style>
