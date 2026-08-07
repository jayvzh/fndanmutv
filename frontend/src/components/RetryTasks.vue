<template>
  <v-container fluid class="pa-4">
    <v-card flat class="rounded border status-card">
      <v-card-title class="text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5 flex-wrap">
        <v-icon icon="mdi-alert-circle-outline" color="warning" size="small" class="mr-2"></v-icon>
        重试任务列表
        <span class="text-sm text-grey ml-2">({{ total }} 个)</span>
        <v-spacer></v-spacer>
        <div class="d-flex align-center" style="gap: 8px;">
          <v-chip v-if="minDanmuCount" size="small" variant="tonal" color="grey">最小弹幕: {{ minDanmuCount }}</v-chip>
          <v-chip v-if="maxRetryTimes" size="small" variant="tonal" color="grey">最大重试: {{ maxRetryTimes }}</v-chip>
          <v-btn color="primary" size="small" variant="tonal" prepend-icon="mdi-refresh" @click="processAll">
            全部重试
          </v-btn>
          <v-btn color="error" size="small" variant="tonal" prepend-icon="mdi-delete" @click="clearAll">
            清空全部
          </v-btn>
        </div>
      </v-card-title>
      <v-card-text class="px-3 py-2">
        <v-data-table
          :headers="headers"
          :items="tasks"
          :items-per-page="10"
          :loading="loading"
          class="elevation-1"
          hide-default-footer
        >
          <template v-slot:item.file_path="{ item }">
            <div class="text-truncate" :title="item.file_path">
              {{ getFileName(item.file_path) }}
            </div>
          </template>
          <template v-slot:item.error_type="{ item }">
            <v-chip :color="getErrorColor(item.error_type)" size="small">
              {{ getErrorLabel(item.error_type) }}
            </v-chip>
          </template>
          <template v-slot:item.actions="{ item }">
            <v-btn icon size="small" color="primary" @click="retrySingle(item.file_path)">
              <v-icon icon="mdi-refresh"></v-icon>
            </v-btn>
            <v-btn icon size="small" color="error" @click="removeSingle(item.file_path)">
              <v-icon icon="mdi-delete"></v-icon>
            </v-btn>
          </template>
        </v-data-table>

        <div v-if="total === 0" class="text-center py-8 text-grey">
          <v-icon icon="mdi-check-circle" size="48" color="success"></v-icon>
          <p class="mt-2">暂无重试任务</p>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const tasks = ref([])
const total = ref(0)
const minDanmuCount = ref(null)
const maxRetryTimes = ref(null)
const loading = ref(false)

const headers = [
  { text: '文件路径', value: 'file_path', width: '30%' },
  { text: '重试次数', value: 'retry_count', width: '10%' },
  { text: '上次尝试', value: 'last_attempt', width: '15%' },
  { text: '下次重试', value: 'next_retry_time', width: '15%' },
  { text: '错误类型', value: 'error_type', width: '10%' },
  { text: '弹幕数量', value: 'last_danmu_count', width: '10%' },
  { text: '操作', value: 'actions', width: '10%' }
]

const fetchTasks = async () => {
  loading.value = true
  try {
    const data = await api.get('/retry_tasks')
    if (data && data.success) {
      tasks.value = Object.values(data.data.tasks || {})
      total.value = data.data.total || 0
      minDanmuCount.value = data.data.min_danmu_count || 100
      maxRetryTimes.value = data.data.max_retry_times || 10
    }
  } catch (error) {
    console.error('获取重试任务失败:', error)
  } finally {
    loading.value = false
  }
}

const processAll = async () => {
  try {
    await api.get('/process_retry_tasks')
    await fetchTasks()
  } catch (error) {
    console.error('处理重试任务失败:', error)
  }
}

const clearAll = async () => {
  try {
    await api.get('/clear_retry_tasks')
    await fetchTasks()
  } catch (error) {
    console.error('清空重试任务失败:', error)
  }
}

const retrySingle = async (filePath) => {
  try {
    await api.get('/generate_danmu', {
      params: { file_path: filePath }
    })
    await fetchTasks()
  } catch (error) {
    console.error('重试单个任务失败:', error)
  }
}

const removeSingle = async (filePath) => {
  try {
    await api.get('/remove_retry_task', {
      params: { file_path: filePath }
    })
    await fetchTasks()
  } catch (error) {
    console.error('移除重试任务失败:', error)
  }
}

const getFileName = (filePath) => {
  return filePath.split('/').pop() || filePath
}

const getErrorLabel = (errorType) => {
  const labels = {
    'rate_limit': '限流',
    'network': '网络',
    'unknown': '未知'
  }
  return labels[errorType] || errorType
}

const getErrorColor = (errorType) => {
  const colors = {
    'rate_limit': 'warning',
    'network': 'error',
    'unknown': 'info'
  }
  return colors[errorType] || 'info'
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped>
.bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.07);
}

.border {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.status-card {
  background-image: linear-gradient(to right, rgba(var(--v-theme-surface), 0.98), rgba(var(--v-theme-surface), 0.95)), 
                    repeating-linear-gradient(45deg, rgba(var(--v-theme-primary), 0.03), rgba(var(--v-theme-primary), 0.03) 10px, transparent 10px, transparent 20px);
  background-attachment: fixed;
  box-shadow: 0 1px 2px rgba(var(--v-border-color), var(--v-border-opacity)) !important;
  transition: all 0.3s ease;
}

.status-card:hover {
  box-shadow: 0 3px 6px rgba(var(--v-border-color), var(--v-border-opacity)) !important;
}
</style>
