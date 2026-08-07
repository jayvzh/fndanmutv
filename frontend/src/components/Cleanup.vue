<template>
  <v-container fluid class="pa-4">
    <v-card flat class="rounded border status-card">
      <v-card-title class="text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5">
        <v-icon icon="mdi-delete-sweep" color="error" size="small" class="mr-2"></v-icon>
        残留弹幕字幕清理
      </v-card-title>
      <v-card-text class="px-3 py-2">
        <v-row class="mb-2">
          <v-col cols="12">
            <v-alert type="info" density="compact" class="text-caption" variant="tonal">
              <v-icon icon="mdi-information" size="small" class="mr-1"></v-icon>
              扫描并清理原视频已删除的残留弹幕字幕文件（.danmu.ass）
            </v-alert>
          </v-col>
        </v-row>
        
        <v-row class="mb-3">
          <v-col cols="12" sm="6">
            <v-select
              v-model="selectedPathsList"
              :items="pathOptions"
              item-title="label"
              item-value="value"
              label="选择扫描路径"
              density="compact"
              variant="outlined"
              hide-details
              multiple
              @update:model-value="handlePathChange"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6">
            <span v-if="!scanPaths.length" class="text-caption text-error">请先在配置中设置媒体库路径</span>
          </v-col>
        </v-row>
        
        <div class="d-flex align-center flex-wrap mb-4" style="gap: 8px;">
          <v-btn color="primary" size="small" variant="tonal" prepend-icon="mdi-search" @click="scanOrphanSubtitles" :loading="scanning" :disabled="!scanPaths.length">
            扫描残留弹幕
          </v-btn>
          <v-btn color="info" size="small" variant="tonal" prepend-icon="mdi-check-all" @click="selectAll" :disabled="!orphanSubtitles.length">
            全选
          </v-btn>
          <v-btn color="error" size="small" variant="tonal" prepend-icon="mdi-delete" @click="cleanSelected" :disabled="!selectedPaths.length" :loading="cleaning">
            清理选中 ({{ selectedPaths.length }})
          </v-btn>
          <v-btn color="error" size="small" variant="tonal" prepend-icon="mdi-delete-forever" @click="cleanAll" :disabled="!orphanSubtitles.length" :loading="cleaning">
            全部删除
          </v-btn>
          <v-spacer></v-spacer>
          <v-chip v-if="totalFound > 0" size="small" variant="tonal" color="primary">找到: {{ totalFound }} 个</v-chip>
          <v-chip v-if="cleanedCount > 0" size="small" variant="tonal" color="success">已清理: {{ cleanedCount }} 个</v-chip>
        </div>

        <div v-if="scanning" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
          <p class="mt-2">正在扫描...</p>
        </div>

        <v-data-table
          v-else
          :headers="headers"
          :items="orphanSubtitles"
          :items-per-page="10"
          :loading="loading"
          class="elevation-1"
          hide-default-footer
        >
          <template v-slot:item.select="{ item }">
            <v-checkbox
              :value="item.path"
              v-model="selectedPaths"
              hide-details
            ></v-checkbox>
          </template>
          <template v-slot:item.path="{ item }">
            <div class="text-caption" :title="item.path">
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

        <div v-if="!scanning && totalFound === 0 && !loading && scanPaths.length" class="text-center py-8 text-grey">
          <v-icon icon="mdi-check-circle" size="48" color="success"></v-icon>
          <p class="mt-2">没有找到残留弹幕字幕文件</p>
        </div>
        
        <div v-if="!scanPaths.length && !scanning" class="text-center py-8 text-grey">
          <v-icon icon="mdi-alert-circle" size="48" color="warning"></v-icon>
          <p class="mt-2">请先在配置中设置媒体库路径</p>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const orphanSubtitles = ref([])
const totalFound = ref(0)
const cleanedCount = ref(0)
const selectedPaths = ref([])
const scanning = ref(false)
const cleaning = ref(false)
const loading = ref(false)
const scanPaths = ref([])
const selectedPathsList = ref([])

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
  { text: '', value: 'select', width: '5%' },
  { text: '文件路径', value: 'path', width: '60%' },
  { text: '大小', value: 'size', width: '15%' },
  { text: '修改时间', value: 'modified_time', width: '20%' }
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
    }
  } catch (error) {
    console.error('清理所有字幕失败:', error)
  } finally {
    cleaning.value = false
  }
}

const selectAll = () => {
  if (selectedPaths.value.length === orphanSubtitles.value.length) {
    selectedPaths.value = []
  } else {
    selectedPaths.value = orphanSubtitles.value.map(item => item.path)
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  fetchConfig()
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
  box-shadow: 0 1px 2px rgba(var(--v-border-color), 0.05) !important;
  transition: all 0.3s ease;
}

.status-card:hover {
  box-shadow: 0 3px 6px rgba(var(--v-border-color), 0.1) !important;
}
</style>
