<template>
  <div>
    <div class="d-flex align-center mb-4 flex-wrap gap-2">
      <v-icon icon="mdi-alert-circle-outline" color="warning" size="22" class="mr-2"></v-icon>
      <span class="section-title-text">重试任务列表</span>
      <span class="text-grey ml-2">({{ total }} 条)</span>
      <v-spacer></v-spacer>
      <div class="d-flex align-center flex-wrap ga-2">
        <v-chip v-if="minDanmuCount" variant="tonal" color="grey" size="small">最小弹幕: {{ minDanmuCount }}</v-chip>
        <v-chip v-if="maxRetryTimes" variant="tonal" color="grey" size="small">最大重试: {{ maxRetryTimes }}</v-chip>
        <v-btn color="primary" variant="tonal" prepend-icon="mdi-refresh" :loading="actionLoading.processAll" @click="processAll">
          全部重试
        </v-btn>
        <v-btn color="error" variant="tonal" prepend-icon="mdi-delete" :loading="actionLoading.clearAll" @click="clearAll">
          清空全部
        </v-btn>
      </div>
    </div>

    <v-alert
      v-if="message.text"
      :type="message.type"
      variant="tonal"
      dismissible
      class="mb-4"
      @click:close="message.text = ''"
    >
      {{ message.text }}
    </v-alert>

    <v-data-table
      :headers="headers"
      :items="tasks"
      :items-per-page="10"
      :loading="loading"
      density="compact"
      class="common-table"
      hide-default-footer
    >
      <template v-slot:item.file_path="{ item }">
        <div class="text-truncate" :title="item.file_path">
          {{ getFileName(item.file_path) }}
        </div>
      </template>
      <template v-slot:item.error_type="{ item }">
        <v-tooltip :text="item.error_message || getErrorLabel(item.error_type)" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-chip v-bind="tooltipProps" :color="getErrorColor(item.error_type)" size="small">
              {{ getErrorLabel(item.error_type) }}
            </v-chip>
          </template>
        </v-tooltip>
      </template>
      <template v-slot:item.actions="{ item }">
        <div class="d-flex ga-1">
          <v-tooltip text="重试" location="top">
            <template #activator="{ props: tooltipProps }">
              <v-btn
                v-bind="tooltipProps"
                icon="mdi-refresh"
                size="small"
                variant="text"
                color="primary"
                :loading="actionLoading['retry_' + item.file_path]"
                @click="retrySingle(item.file_path)"
              ></v-btn>
            </template>
          </v-tooltip>
          <v-tooltip text="删除" location="top">
            <template #activator="{ props: tooltipProps }">
              <v-btn
                v-bind="tooltipProps"
                icon="mdi-delete-outline"
                size="small"
                variant="text"
                color="error"
                :loading="actionLoading['remove_' + item.file_path]"
                @click="removeSingle(item.file_path)"
              ></v-btn>
            </template>
          </v-tooltip>
        </div>
      </template>
    </v-data-table>

    <div v-if="total === 0" class="empty-state text-center py-12 text-grey">
      <v-icon icon="mdi-check-circle" size="64" color="success"></v-icon>
      <p class="text-h6 mt-4 mb-0">暂无重试任务</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import api from '../api'

const tasks = ref([])
const total = ref(0)
const minDanmuCount = ref(null)
const maxRetryTimes = ref(null)
const loading = ref(false)
const actionLoading = reactive({
  processAll: false,
  clearAll: false
})
const message = reactive({
  text: '',
  type: 'success'
})
let messageTimer = null

const showMessage = (text, type = 'success') => {
  message.text = text
  message.type = type
  if (messageTimer) clearTimeout(messageTimer)
  messageTimer = setTimeout(() => {
    message.text = ''
  }, 4000)
}

const headers = [
  { title: '文件路径', value: 'file_path', width: '30%' },
  { title: '重试次数', value: 'retry_count', width: '10%' },
  { title: '上次尝试', value: 'last_attempt', width: '15%' },
  { title: '下次重试', value: 'next_retry_time', width: '15%' },
  { title: '错误类型', value: 'error_type', width: '10%' },
  { title: '弹幕数量', value: 'last_danmu_count', width: '10%' },
  { title: '操作', value: 'actions', width: '90', sortable: false }
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
  actionLoading.processAll = true
  try {
    const res = await api.get('/process_retry_tasks')
    if (res && res.success) {
      showMessage(res.message || '全部重试任务已启动', 'success')
    } else {
      showMessage(res?.message || '全部重试失败', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('处理重试任务失败:', error)
    showMessage('全部重试失败，请检查网络或API', 'error')
  } finally {
    actionLoading.processAll = false
  }
}

const clearAll = async () => {
  actionLoading.clearAll = true
  try {
    const res = await api.get('/clear_retry_tasks')
    if (res && res.success) {
      showMessage(res.message || '已清空全部重试任务', 'success')
    } else {
      showMessage(res?.message || '清空失败', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('清空重试任务失败:', error)
    showMessage('清空失败，请检查网络或API', 'error')
  } finally {
    actionLoading.clearAll = false
  }
}

const retrySingle = async (filePath) => {
  actionLoading['retry_' + filePath] = true
  try {
    const res = await api.get('/generate_danmu', {
      params: { file_path: filePath }
    })
    if (res && res.success) {
      showMessage(res.message || `已重试：${getFileName(filePath)}`, 'success')
    } else {
      showMessage(res?.message || '重试失败', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('重试单个任务失败:', error)
    showMessage('重试失败，请检查网络或API', 'error')
  } finally {
    delete actionLoading['retry_' + filePath]
  }
}

const removeSingle = async (filePath) => {
  actionLoading['remove_' + filePath] = true
  try {
    const res = await api.get('/remove_retry_task', {
      params: { file_path: filePath }
    })
    if (res && res.success) {
      showMessage(res.message || `已移除：${getFileName(filePath)}`, 'success')
    } else {
      showMessage(res?.message || '移除失败', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('移除重试任务失败:', error)
    showMessage('移除失败，请检查网络或API', 'error')
  } finally {
    delete actionLoading['remove_' + filePath]
  }
}

const getFileName = (filePath) => {
  if (!filePath) return ''
  return filePath.split(/[\\/]/).pop() || filePath
}

const getErrorLabel = (errorType) => {
  const labels = {
    'rate_limit': '429限流',
    'no_data': '无弹幕',
    'no_match': '未匹配',
    'network': '网络错误',
    'unknown': '未知'
  }
  return labels[errorType] || '未知'
}

const getErrorColor = (errorType) => {
  const colors = {
    'rate_limit': 'warning',
    'no_data': 'grey',
    'no_match': 'grey',
    'network': 'error',
    'unknown': 'grey'
  }
  return colors[errorType] || 'grey'
}

onMounted(() => {
  fetchTasks()
})

onUnmounted(() => {
  if (messageTimer) clearTimeout(messageTimer)
})
</script>

<style scoped>
.section-title-text {
  font-size: 1.1rem;
  font-weight: 600;
  line-height: 1.2;
}

.common-table {
  border-radius: 8px;
}

.common-table :deep(thead th) {
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  white-space: nowrap;
  color: rgb(var(--v-theme-on-surface)) !important;
}

.common-table :deep(tbody td) {
  font-size: 0.8rem !important;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
