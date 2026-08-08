<template>
  <v-container fluid class="pa-4">
    <v-card flat class="rounded border status-card">
      <v-card-title class="text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5">
        <v-icon icon="mdi-history" color="primary" size="small" class="mr-2"></v-icon>
        历史记录
        <span class="text-sm text-grey ml-2">({{ total }} 条)</span>
        <v-spacer></v-spacer>
        <v-btn color="error" size="small" variant="tonal" prepend-icon="mdi-delete" @click="clearHistory">
          清空历史
        </v-btn>
      </v-card-title>
      <v-card-text class="px-3 py-2">
        <v-data-table
          :headers="headers"
          :items="history"
          :items-per-page="10"
          :loading="loading"
          density="compact"
          class="elevation-1 history-table"
          item-key="id"
          show-expand
        >
          <template v-slot:item.timestamp="{ item }">
            {{ formatTime(item.timestamp) }}
          </template>
          <template v-slot:item.type="{ item }">
            <v-chip :color="getTypeColor(item.type)" size="small">
              {{ getTypeLabel(item.type) }}
            </v-chip>
          </template>
          <template v-slot:item.path="{ item }">
            <div class="text-truncate" :title="item.path">
              {{ item.path }}
            </div>
          </template>
          <template v-slot:item.result="{ item }">
            <span class="text-success">成功 {{ item.success }}</span>
            <span class="mx-2">/</span>
            <span class="text-error">失败 {{ item.failed }}</span>
          </template>
          <template v-slot:item.duration="{ item }">
            {{ formatDuration(item.duration) }}
          </template>
          <template v-slot:expanded-item="{ item }">
            <td colspan="7">
              <div v-if="item.details && item.details.length > 0">
                <v-data-table
                  :headers="detailHeaders"
                  :items="item.details"
                  hide-default-footer
                  density="compact"
                  class="elevation-0"
                >
                  <template v-slot:item.result="{ item }">
                    <v-icon :icon="item.result === 'success' ? 'mdi-check-circle' : 'mdi-close-circle'" 
                             :color="item.result === 'success' ? 'success' : 'error'" 
                             size="small"></v-icon>
                  </template>
                  <template v-slot:item.error="{ item }">
                    <span v-if="item.error" class="text-error text-caption">{{ item.error }}</span>
                    <span v-else class="text-grey">-</span>
                  </template>
                </v-data-table>
              </div>
              <div v-else class="text-grey text-sm">暂无详情</div>
            </td>
          </template>
        </v-data-table>

        <div v-if="total === 0" class="text-center py-8 text-grey">
          <v-icon icon="mdi-history" size="48"></v-icon>
          <p class="mt-2">暂无历史记录</p>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  api: { 
    type: [Object, Function],
    required: true,
  }
})

const history = ref([])
const total = ref(0)
const loading = ref(false)

const headers = [
  { title: '时间', value: 'timestamp', width: '18%' },
  { title: '类型', value: 'type', width: '10%' },
  { title: '路径', value: 'path', width: '30%' },
  { title: '处理数', value: 'processed', width: '10%' },
  { title: '结果', value: 'result', width: '15%' },
  { title: '耗时', value: 'duration', width: '10%' }
]

const detailHeaders = [
  { title: '文件', value: 'file', width: '40%' },
  { title: '结果', value: 'result', width: '10%' },
  { title: '弹幕数', value: 'danmu_count', width: '10%' },
  { title: '错误信息', value: 'error', width: '40%' }
]

const fetchHistory = async () => {
  loading.value = true
  try {
    const data = await props.api.get('plugin/DanmuTV/history', {
      params: { include_details: true }
    })
    if (data && data.success) {
      history.value = data.data.history || []
      total.value = data.data.total || 0
    }
  } catch (error) {
    console.error('获取历史记录失败:', error)
  } finally {
    loading.value = false
  }
}

const clearHistory = async () => {
  try {
    await props.api.post('plugin/DanmuTV/clear_history')
    await fetchHistory()
  } catch (error) {
    console.error('清空历史记录失败:', error)
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}

const formatDuration = (seconds) => {
  if (!seconds) return '0秒'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`
}

const getTypeLabel = (type) => {
  const labels = {
    'batch': '批量刮削',
    'single': '单文件刮削',
    'retry': '重试任务'
  }
  return labels[type] || type
}

const getTypeColor = (type) => {
  const colors = {
    'batch': 'primary',
    'single': 'info',
    'retry': 'warning'
  }
  return colors[type] || 'info'
}

onMounted(() => {
  fetchHistory()
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

.history-table :deep(thead) {
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.history-table :deep(th) {
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  white-space: nowrap;
}

.history-table :deep(td) {
  font-size: 0.75rem !important;
}
</style>
