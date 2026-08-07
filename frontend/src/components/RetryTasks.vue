<template>
  <div>
    <div class="d-flex align-center mb-4 flex-wrap gap-2">
      <v-icon icon="mdi-alert-circle-outline" color="warning" size="22" class="mr-2"></v-icon>
      <span class="section-title-text">重试任务列表</span>
      <v-chip label size="small" variant="tonal" color="grey">{{ total }}</v-chip>
      <v-spacer></v-spacer>
      <div class="d-flex align-center gap-2 flex-wrap">
        <v-chip v-if="minDanmuCount" variant="tonal" color="grey">最小弹幕: {{ minDanmuCount }}</v-chip>
        <v-chip v-if="maxRetryTimes" variant="tonal" color="grey">最大重试: {{ maxRetryTimes }}</v-chip>
        <v-btn color="primary" variant="tonal" prepend-icon="mdi-refresh" @click="processAll">
          全部重试
        </v-btn>
        <v-btn color="error" variant="tonal" prepend-icon="mdi-delete" @click="clearAll">
          清空全部
        </v-btn>
      </div>
    </div>

    <v-data-table
      :headers="headers"
      :items="tasks"
      :items-per-page="10"
      :loading="loading"
      density="comfortable"
      class="retry-table"
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
        <v-btn icon color="primary" @click="retrySingle(item.file_path)">
          <v-icon icon="mdi-refresh"></v-icon>
        </v-btn>
        <v-btn icon color="error" @click="removeSingle(item.file_path)">
          <v-icon icon="mdi-delete"></v-icon>
        </v-btn>
      </template>
    </v-data-table>

    <div v-if="total === 0" class="empty-state text-center py-12 text-grey">
      <v-icon icon="mdi-check-circle" size="64" color="success"></v-icon>
      <p class="text-h6 mt-4 mb-0">暂无重试任务</p>
    </div>
  </div>
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
.section-title-text {
  font-size: 1.1rem;
  font-weight: 600;
  line-height: 1.2;
}

.retry-table {
  border-radius: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
