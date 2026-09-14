<template>
  <div>
    <div class="d-flex align-center mb-4 flex-wrap ga-2">
      <v-icon icon="mdi-delete-sweep" color="error" size="22" class="mr-2"></v-icon>
      <span
        class="section-title-text"
        v-tooltip="'扫描并清理原视频已删除的残留弹幕字幕文件（.danmu.ass）'"
      >孤儿弹幕字幕清理</span>
      <v-select
        v-model="selectedPathsList"
        :items="pathOptions"
        item-title="label"
        item-value="value"
        label="选择扫描路径"
        variant="outlined"
        hide-details
        density="compact"
        multiple
        :menu-props="{ contentClass: 'compact-select-menu' }"
        class="cleanup-select"
        style="max-width: 360px"
        @update:model-value="handlePathChange"
      ></v-select>
      <span v-if="!scanPaths.length" class="text-error text-body-2">请先在配置中设置媒体库路径</span>
      <v-spacer></v-spacer>
      <div class="d-flex align-center flex-wrap ga-2 cleanup-actions">
        <v-btn color="primary" variant="tonal" prepend-icon="mdi-radar" @click="scanOrphanSubtitles" :loading="scanning" :disabled="!scanPaths.length">
          <span class="d-none d-sm-inline">扫描残留</span><span class="d-sm-none">扫描</span>
        </v-btn>
        <v-btn color="error" variant="tonal" prepend-icon="mdi-delete" @click="cleanSelected" :disabled="!selectedPaths.length" :loading="cleaning">
          <span class="d-none d-sm-inline">清理选中 ({{ selectedPaths.length }})</span><span class="d-sm-none">清已选</span>
        </v-btn>
        <v-btn color="error" variant="tonal" prepend-icon="mdi-delete-forever" @click="cleanAll" :disabled="!orphanSubtitles.length" :loading="cleaning">
          <span class="d-none d-sm-inline">全部删除</span><span class="d-sm-none">全删</span>
        </v-btn>
      </div>
    </div>

    <div v-if="scanning" class="text-center py-10">
      <v-progress-circular indeterminate color="primary" size="72"></v-progress-circular>
      <p class="mt-4 text-body-1">正在扫描...</p>
    </div>

    <v-data-table
      v-else
      :headers="headers"
      :items="orphanSubtitles"
      :items-per-page="10"
      :loading="loading"
      density="compact"
      class="common-table"
    >
      <template v-slot:header.select>
        <v-checkbox
          :model-value="isAllSelected"
          :indeterminate="isIndeterminate"
          hide-details
          density="compact"
          class="justify-center"
          @update:model-value="toggleSelectAll"
        ></v-checkbox>
      </template>
      <template v-slot:item.select="{ item }">
        <v-checkbox
          :value="item.path"
          v-model="selectedPaths"
          hide-details
          density="compact"
          class="justify-center"
        ></v-checkbox>
      </template>
      <template v-slot:item.path="{ item }">
        <div class="text-body-2" :title="item.path">
          {{ item.path }}
        </div>
      </template>
      <template v-slot:item.size="{ item }">
        {{ formatSize(item.size) }}
      </template>
      <template v-slot:item.modified_time="{ item }">
        {{ item.modified_time }}
      </template>
    </v-data-table>

    <div v-if="!scanning && totalFound === 0 && !loading && scanPaths.length" class="text-center py-10 text-grey">
      <v-icon icon="mdi-check-circle" size="64" color="success"></v-icon>
      <p class="mt-3 text-h6">没有找到残留弹幕字幕文件</p>
    </div>

    <div v-if="!scanPaths.length && !scanning" class="text-center py-10 text-grey">
      <v-icon icon="mdi-alert-circle" size="64" color="warning"></v-icon>
      <p class="mt-3 text-h6">请先在配置中设置媒体库路径</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../api'
import { CLEANUP_CACHE_KEY, readCache, writeCache } from '../utils/cache'

const orphanSubtitles = ref([])
const totalFound = ref(0)
const cleanedCount = ref(0)
const selectedPaths = ref([])
const scanning = ref(false)
const cleaning = ref(false)
const loading = ref(false)
const scanPaths = ref([])
const selectedPathsList = ref([])

// 扫描结果持久化到 localStorage：切 tab / 刷新页面不丢失，重新扫描或清理后更新
function persistCleanup() {
  writeCache(CLEANUP_CACHE_KEY, {
    items: orphanSubtitles.value,
    total: totalFound.value,
  })
}

watch([orphanSubtitles, totalFound], persistCleanup)

const pathOptions = computed(() => {
  const options = []
  if (scanPaths.value.length > 0) {
    options.push({ label: '全部媒体库路径', value: '__all__' })
    scanPaths.value.forEach((path, index) => {
      options.push({ label: path, value: path })
    })
  }
  return options
})

const headers = [
  { title: '', value: 'select', width: '5%', align: 'center' },
  { title: '文件路径', value: 'path', width: '60%' },
  { title: '大小', value: 'size', width: '15%' },
  { title: '修改时间', value: 'modified_time', width: '20%' }
]

const handlePathChange = (newVal) => {
  if (!newVal || newVal.length === 0) {
    selectedPathsList.value = ['__all__']
  }
}

const getScanPaths = () => {
  if (!selectedPathsList.value || selectedPathsList.value.length === 0) {
    return scanPaths.value
  }
  if (selectedPathsList.value.includes('__all__')) {
    return scanPaths.value
  }
  return selectedPathsList.value
}

const scanOrphanSubtitles = async () => {
  scanning.value = true
  selectedPaths.value = []
  try {
    const paths = getScanPaths()
    const data = await api.get('/scan_orphan_subtitles', {
      params: { path: paths.join('\n') }
    })
    if (data && data.success) {
      orphanSubtitles.value = data.data.orphan_subtitles || []
      totalFound.value = data.data.total_found || 0
      // 扫描结果改为右下角通知（复用全局 app:notify；>0 为成功，0 个为中性信息）
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: {
          type: totalFound.value > 0 ? 'success' : 'info',
          title: '扫描完成',
          text: totalFound.value > 0 ? `扫描到 ${totalFound.value} 个残留弹幕字幕文件` : '未扫描到残留弹幕字幕文件',
        }
      }))
    }
  } catch (error) {
    console.error('扫描残留弹幕失败:', error)
  } finally {
    scanning.value = false
  }
}

const fetchConfig = async () => {
  try {
    const data = await api.get('/config')
    if (data) {
      // /config 端点直接返回配置对象，没有 success/data 包装
      const path = data.path || ''
      scanPaths.value = path.split('\n').filter(p => p.trim())
      if (scanPaths.value.length > 0) {
        selectedPathsList.value = ['__all__']
      }
    }
  } catch (error) {
    console.error('获取配置失败:', error)
  }
}

const cleanSingle = async (filePath) => {
  try {
    const data = await api.post('/clean_orphan_subtitles', [filePath])
    if (data && data.success) {
      cleanedCount.value += data.data.cleaned_count || 0
      orphanSubtitles.value = orphanSubtitles.value.filter(item => item.path !== filePath)
      totalFound.value = orphanSubtitles.value.length
    }
  } catch (error) {
    console.error('清理字幕文件失败:', error)
  }
}

const cleanSelected = async () => {
  if (!selectedPaths.value.length) return
  cleaning.value = true
  try {
    const data = await api.post('/clean_orphan_subtitles', selectedPaths.value)
    if (data && data.success) {
      cleanedCount.value += data.data.cleaned_count || 0
      orphanSubtitles.value = orphanSubtitles.value.filter(item => !selectedPaths.value.includes(item.path))
      totalFound.value = orphanSubtitles.value.length
      selectedPaths.value = []
      // 删除结果改为右下角通知（复用全局 app:notify）
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: { success: true, title: '清理完成', text: `本次删除 ${data.data.cleaned_count || 0} 个残留字幕文件` }
      }))
    }
  } catch (error) {
    console.error('清理选中字幕失败:', error)
  } finally {
    cleaning.value = false
  }
}

const cleanAll = async () => {
  if (!orphanSubtitles.value.length) return
  if (!confirm('确定要删除所有找到的残留弹幕字幕文件吗？此操作不可恢复。')) {
    return
  }
  cleaning.value = true
  try {
    const paths = orphanSubtitles.value.map(item => item.path)
    const data = await api.post('/clean_orphan_subtitles', paths)
    if (data && data.success) {
      cleanedCount.value += data.data.cleaned_count || 0
      orphanSubtitles.value = []
      totalFound.value = 0
      selectedPaths.value = []
      // 删除结果改为右下角通知（复用全局 app:notify）
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: { success: true, title: '清理完成', text: `本次删除 ${data.data.cleaned_count || 0} 个残留字幕文件` }
      }))
    }
  } catch (error) {
    console.error('清理所有字幕失败:', error)
  } finally {
    cleaning.value = false
  }
}

const isAllSelected = computed(() =>
  orphanSubtitles.value.length > 0 && selectedPaths.value.length === orphanSubtitles.value.length
)

const isIndeterminate = computed(() =>
  selectedPaths.value.length > 0 && selectedPaths.value.length < orphanSubtitles.value.length
)

const toggleSelectAll = () => {
  selectedPaths.value = isAllSelected.value ? [] : orphanSubtitles.value.map(item => item.path)
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  // 恢复上次扫描结果（不重新扫描）
  const cached = readCache(CLEANUP_CACHE_KEY)
  if (cached && Array.isArray(cached.items) && cached.items.length > 0) {
    orphanSubtitles.value = cached.items
    totalFound.value = cached.total || cached.items.length
  }
  fetchConfig()
})
</script>

<style scoped>
.section-title-text {
  font-size: 1.1rem;
  font-weight: 600;
  line-height: 1.2;
}

.cleanup-select {
  margin-left: 16px; /* 替代原 ml-4，便于移动端归零 */
}

/* 移动端（<600px）：下拉独占一行与标题留距，按钮组独占一行保持间距 */
@media (max-width: 599.98px) {
  .cleanup-select {
    flex: 1 1 100%;
    margin-left: 0;
    margin-top: 12px;
    max-width: 100%;
  }

  .cleanup-actions {
    flex: 1 1 100%;
    margin-top: 12px;
  }
}

.cleanup-select :deep(.v-select__selection-text),
.cleanup-select :deep(.v-select__placeholder),
.cleanup-select :deep(.v-field__input) {
  font-size: 0.9rem;
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

.common-table :deep(.v-selection-control) {
  --v-selection-control-size: 28px;
}
</style>
