<template>
  <div class="dashboard-view">
    <!-- 插件状态栏 -->
    <v-card class="section-card mb-5" elevation="0">
      <v-card-title class="section-title d-flex align-center">
        <v-icon icon="mdi-information" color="primary" size="20" class="mr-2"></v-icon>
        插件状态
      </v-card-title>
      <v-card-text class="pt-2">
        <v-row>
          <v-col cols="12" sm="4">
            <div class="status-item d-flex align-center py-3">
              <v-avatar :color="enabled ? 'success' : 'error'" size="44" class="mr-4">
                <v-icon :icon="enabled ? 'mdi-check' : 'mdi-close'" size="24" color="white"></v-icon>
              </v-avatar>
              <div class="status-content flex-grow-1">
                <div class="status-label">插件启用</div>
                <div class="status-value" :class="enabled ? 'text-success' : 'text-error'">{{ enabled ? '已启用' : '未启用' }}</div>
              </div>
            </div>
          </v-col>
          <v-col cols="12" sm="4">
            <div class="status-item d-flex align-center py-3">
              <v-avatar :color="apiConnected ? 'success' : 'error'" size="44" class="mr-4">
                <v-icon :icon="apiConnected ? 'mdi-web' : 'mdi-web-off'" size="24" color="white"></v-icon>
              </v-avatar>
              <div class="status-content flex-grow-1">
                <div class="status-label">API状态</div>
                <div class="status-value" :class="apiConnected ? 'text-success' : 'text-error'">{{ apiConnected ? '正常' : '异常' }}</div>
              </div>
            </div>
          </v-col>
          <v-col cols="12" sm="4">
            <div class="status-item d-flex align-center py-3">
              <v-avatar :color="mediaLibraryAccessible ? 'success' : 'error'" size="44" class="mr-4">
                <v-icon :icon="mediaLibraryAccessible ? 'mdi-folder-check' : 'mdi-folder-alert'" size="24" color="white"></v-icon>
              </v-avatar>
              <div class="status-content flex-grow-1">
                <div class="status-label">媒体库</div>
                <div class="status-value" :class="mediaLibraryAccessible ? 'text-success' : 'text-error'">
                  {{ mediaLibraryAccessible ? `可访问 (${mediaLibraryCount})` : '不可访问' }}
                </div>
              </div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 统计信息栏 -->
    <v-card class="section-card mb-5" elevation="0">
      <v-card-title class="section-title d-flex align-center">
        <v-icon icon="mdi-chart-bar" color="primary" size="20" class="mr-2"></v-icon>
        统计信息
      </v-card-title>
      <v-card-text class="pt-2">
        <v-row>
          <v-col cols="6" sm="3">
            <div class="stat-item text-center py-3">
              <div class="stat-number text-primary">{{ stats.total_files }}</div>
              <div class="stat-label text-grey">媒体库文件</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3">
            <div class="stat-item text-center py-3">
              <div class="stat-number text-success">{{ stats.success_count }}</div>
              <div class="stat-label text-grey">已刮削</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3">
            <div class="stat-item text-center py-3">
              <div class="stat-number text-error">{{ stats.failed_count }}</div>
              <div class="stat-label text-grey">失败</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3">
            <div class="stat-item text-center py-3">
              <div class="stat-number text-warning">{{ stats.retry_tasks_count }}</div>
              <div class="stat-label text-grey">待重试</div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 最近运行栏 -->
    <v-card class="section-card mb-5" elevation="0">
      <v-card-title class="section-title d-flex align-center">
        <v-icon icon="mdi-history" color="primary" size="20" class="mr-2"></v-icon>
        最近运行
      </v-card-title>
      <v-card-text class="pt-3">
        <v-row>
          <v-col cols="12" sm="6">
            <div class="d-flex align-center justify-space-between py-2">
              <div class="d-flex align-center">
                <v-icon icon="mdi-clock-outline" color="primary" class="mr-2"></v-icon>
                <span class="text-body-1">最近运行时间</span>
              </div>
              <div v-if="lastRun" class="text-body-1 font-weight-bold text-primary d-flex align-center">
                {{ formatTime(lastRun.timestamp) }}
                <v-chip size="small" color="primary" variant="tonal" class="ml-2">{{ getTypeLabel(lastRun.type) }}</v-chip>
              </div>
              <span v-else class="text-body-1 text-grey">暂无记录</span>
            </div>
          </v-col>
          <v-col cols="12" sm="6">
            <div class="d-flex align-center justify-space-between py-2">
              <div class="d-flex align-center">
                <v-icon icon="mdi-calendar-clock" color="warning" class="mr-2"></v-icon>
                <span class="text-body-1">下次运行时间</span>
              </div>
              <div v-if="nextRetryTime" class="text-body-1 font-weight-bold text-warning d-flex align-center">
                {{ nextRetryTime }}
                <v-chip size="small" color="warning" variant="tonal" class="ml-2">单个重试</v-chip>
              </div>
              <span v-else class="text-body-1 text-grey">暂无重试任务</span>
            </div>
          </v-col>
        </v-row>
        <v-row v-if="lastRun" class="mt-2">
          <v-col cols="12">
            <v-btn color="primary" variant="tonal" @click="triggerRetry" :disabled="!stats.retry_tasks_count" prepend-icon="mdi-refresh">
              立即重试 ({{ stats.retry_tasks_count }})
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 刮削进度 -->
    <v-card v-if="scrapingStatus.running" class="section-card progress-card" elevation="0">
      <v-card-title class="section-title d-flex align-center">
        <v-icon icon="mdi-loader" color="primary" class="mr-2 animate-spin"></v-icon>
        正在刮削中
      </v-card-title>
      <v-card-text class="pt-3">
        <v-progress-linear
          :value="scrapingStatus.total > 0 ? (scrapingStatus.processed / scrapingStatus.total * 100) : 0"
          color="primary"
          height="10"
          rounded
        ></v-progress-linear>
        <div class="d-flex justify-between mt-3 text-body-2">
          <span>当前文件: {{ scrapingStatus.current_file }}</span>
          <span class="font-weight-bold">{{ scrapingStatus.processed }} / {{ scrapingStatus.total }}</span>
        </div>
        <div class="d-flex justify-between mt-1 text-body-2">
          <span>成功: <span class="text-success font-weight-medium">{{ scrapingStatus.success }}</span> | 失败: <span class="text-error font-weight-medium">{{ scrapingStatus.failed }}</span></span>
          <span>耗时: {{ formatDuration(scrapingStatus.duration) }}</span>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../api'

const enabled = ref(false)
const apiConnected = ref(false)
const apiMessage = ref('')
const mediaLibraryAccessible = ref(false)
const mediaLibraryCount = ref(0)
const stats = ref({ total_files: 0, success_count: 0, failed_count: 0, retry_tasks_count: 0 })
const nextRetryTime = ref(null)
const lastRun = ref(null)
const scrapingStatus = ref({ running: false, total: 0, processed: 0, success: 0, failed: 0, current_file: null, duration: 0 })

let refreshInterval = null

const fetchStatus = async () => {
  try {
    const data = await api.get('/full_status');
    if (data && data.success) {
      const result = data.data
      enabled.value = result.enabled
      apiConnected.value = result.api_connected
      apiMessage.value = result.api_message
      mediaLibraryAccessible.value = result.media_library_accessible
      mediaLibraryCount.value = result.media_library_count || 0
      stats.value = result.stats
      nextRetryTime.value = result.next_retry_time
      lastRun.value = result.last_run
      scrapingStatus.value = {
        running: result.running,
        total: result.total,
        processed: result.processed,
        success: result.success,
        failed: result.failed,
        current_file: result.current_file,
        duration: result.duration
      }
    }
  } catch (error) {
    console.error('获取状态失败:', error)
  }
}

const triggerRetry = async () => {
  try {
    await api.get('/process_retry_tasks')
    await fetchStatus()
  } catch (error) {
    console.error('触发重试失败:', error)
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
  const labels = { 'batch': '批量刮削', 'single': '单文件刮削', 'retry': '重试任务' }
  return labels[type] || type
}

onMounted(() => {
  fetchStatus()
  refreshInterval = setInterval(fetchStatus, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.section-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #FFFFFF;
  transition: box-shadow 0.2s ease;
}

.section-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.section-title {
  font-size: 1rem !important;
  font-weight: 600;
  padding: 1rem 1.25rem 0.5rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.status-item {
  border-radius: 10px;
  transition: background-color 0.2s ease;
}

.status-item:hover {
  background-color: rgba(25, 118, 210, 0.04);
}

.status-label {
  font-size: 0.9rem;
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 2px;
}

.status-value {
  font-size: 1rem;
  font-weight: 600;
}

.stat-item {
  border-radius: 10px;
  transition: background-color 0.2s ease;
}

.stat-item:hover {
  background-color: rgba(25, 118, 210, 0.04);
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.1;
}

.stat-label {
  font-size: 0.85rem;
  margin-top: 4px;
}

.progress-card {
  background: linear-gradient(135deg, rgba(25, 118, 210, 0.04), rgba(25, 118, 210, 0.01));
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
