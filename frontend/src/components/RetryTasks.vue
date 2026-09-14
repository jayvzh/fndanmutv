<template>
  <div>
    <div class="d-flex align-center mb-4 flex-wrap ga-2">
      <v-icon icon="mdi-alert-circle-outline" color="warning" size="22" class="mr-2"></v-icon>
      <span class="section-title-text">重试任务列表</span>
      <span class="text-grey ml-2">({{ total }} 条)</span>
      <v-spacer></v-spacer>
      <div class="d-flex align-center ga-2 retry-chips">
        <v-chip v-if="minDanmuCount" variant="tonal" color="grey" size="small">最小弹幕: {{ minDanmuCount }}</v-chip>
        <v-chip v-if="maxRetryTimes" variant="tonal" color="grey" size="small">最大重试: {{ maxRetryTimes }}</v-chip>
      </div>
      <div class="d-flex align-center ga-2 retry-action-btns">
        <v-btn color="primary" variant="tonal" prepend-icon="mdi-refresh" :loading="actionLoading.processAll" @click="processAll">
          全部重试
        </v-btn>
        <v-btn color="error" variant="tonal" prepend-icon="mdi-delete" :loading="actionLoading.clearAll" @click="clearAll">
          清空全部
        </v-btn>
      </div>
    </div>

    <v-data-table
      :headers="headers"
      :items="tasks"
      :items-per-page="10"
      :loading="loading"
      density="compact"
      class="common-table"
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
// 全局右下角通知（复用 App.vue 的 app:notify），替代原页内 v-alert
const notify = (title, text, type = 'success') => {
  window.dispatchEvent(new CustomEvent('app:notify', { detail: { type, title, text } }))
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
      notify('全部重试', res.message || '全部重试任务已启动', 'success')
    } else {
      notify('全部重试失败', res?.message || '请稍后重试', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('处理重试任务失败:', error)
    notify('全部重试失败', '请检查网络或API', 'error')
  } finally {
    actionLoading.processAll = false
  }
}

const clearAll = async () => {
  actionLoading.clearAll = true
  try {
    const res = await api.get('/clear_retry_tasks')
    if (res && res.success) {
      notify('清空完成', res.message || '已清空全部重试任务', 'success')
    } else {
      notify('清空失败', res?.message || '请稍后重试', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('清空重试任务失败:', error)
    notify('清空失败', '请检查网络或API', 'error')
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
      notify('重试成功', res.message || `已重试：${getFileName(filePath)}`, 'success')
    } else {
      notify('重试失败', res?.message || '请稍后重试', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('重试单个任务失败:', error)
    notify('重试失败', '请检查网络或API', 'error')
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
      notify('移除成功', res.message || `已移除：${getFileName(filePath)}`, 'success')
    } else {
      notify('移除失败', res?.message || '请稍后重试', 'error')
    }
    await fetchTasks()
  } catch (error) {
    console.error('移除重试任务失败:', error)
    notify('移除失败', '请检查网络或API', 'error')
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
  overflow: hidden;
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
  padding-top: 6px !important;
  padding-bottom: 6px !important;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* 移动端（<600px）：按钮组独占一行，「全部重试」前换行，两行均居中 */
@media (max-width: 599.98px) {
  .retry-action-btns {
    flex: 1 1 100%;
    justify-content: center;
  }

  /* chips 独占一行且保持一行不拆分 */
  .retry-chips {
    flex: 1 1 100%;
    flex-wrap: nowrap;
    justify-content: center;
  }
}
</style>
