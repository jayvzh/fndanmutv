<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-icon icon="mdi-history" color="primary" size="22" class="mr-2"></v-icon>
      <span class="section-title-text">历史记录</span>
      <span class="text-grey ml-2">({{ total }} 条)</span>
      <v-spacer></v-spacer>
      <v-btn color="error" variant="tonal" prepend-icon="mdi-delete" @click="clearHistory">
        清空历史
      </v-btn>
    </div>

    <v-data-table
      :headers="headers"
      :items="history"
      :items-per-page="10"
      :loading="loading"
      density="compact"
      show-expand
      class="common-table"
      item-key="id"
    >
      <template v-slot:item.data-table-expand="{ item, internalItem, isExpanded, toggleExpand }">
        <v-btn
          v-if="canExpand(item)"
          icon
          size="x-small"
          variant="text"
          :ripple="false"
          :aria-label="isExpanded(internalItem) ? '收起' : '展开'"
          @click="onToggleExpand(item, internalItem, isExpanded, toggleExpand)"
        >
          <v-icon :icon="isExpanded(internalItem) ? 'mdi-chevron-up' : 'mdi-chevron-down'" />
        </v-btn>
      </template>
      <template v-slot:item.timestamp="{ item }">
        {{ formatTime(item.timestamp) }}
      </template>
      <template v-slot:item.type="{ item }">
        <v-chip :color="getTypeColor(item.type)">
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
      <template v-slot:expanded-row="{ columns, item }">
        <tr>
          <td :colspan="columns.length">
            <div v-if="item.details && item.details.length > 0" class="pa-2">
              <v-data-table
                :headers="detailHeaders"
                :items="item.details"
                hide-default-footer
                density="compact"
                class="elevation-0 common-table"
              >
                <template v-slot:item.result="{ item: detail }">
                  <v-icon :icon="detail.result === 'success' ? 'mdi-check-circle' : 'mdi-close-circle'"
                           :color="detail.result === 'success' ? 'success' : 'error'"></v-icon>
                </template>
                <template v-slot:item.error="{ item: detail }">
                  <span v-if="detail.error" class="text-error text-wrap">{{ detail.error }}</span>
                  <span v-else class="text-grey">-</span>
                </template>
              </v-data-table>
            </div>
            <div v-else class="pa-3 text-grey">无详情</div>
          </td>
        </tr>
      </template>
    </v-data-table>

    <div v-if="total === 0" class="text-center py-12 text-grey">
      <v-icon icon="mdi-history" size="64"></v-icon>
      <p class="text-h6 mt-4 mb-0">暂无历史记录</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

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
    const data = await api.get('/history', {
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
    await api.post('/clear_history')
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

// 仅当存在详情（有错误信息，或开启详情开关时记录的成功项）时才显示展开按钮
const canExpand = (item) => {
  return !!(item && item.details && item.details.length > 0)
}

// 展开/收起单行（使用 internalItem，Vuetify 内部对象），带排查日志
const onToggleExpand = (item, internalItem, isExpanded, toggleExpand) => {
  const before = isExpanded(internalItem)
  console.log('[History] toggle expand clicked', {
    id: item?.id,
    type: item?.type,
    detailsLen: item?.details?.length,
    beforeExpanded: before,
    internalItemValue: !!internalItem?.value
  })
  if (!internalItem) {
    console.error('[History] internalItem 缺失，无法切换展开状态')
    return
  }
  toggleExpand(internalItem)
  // 下一帧确认状态
  requestAnimationFrame(() => {
    console.log('[History] after toggle, isExpanded =', isExpanded(internalItem))
  })
}

onMounted(() => {
  fetchHistory()
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

.text-wrap {
  white-space: normal;
  word-break: break-word;
}
</style>
