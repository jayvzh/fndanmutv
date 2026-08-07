<template>
  <div class="browse-view">
    <div class="section-title d-flex align-center mb-4">
      <v-icon icon="mdi-folder" color="primary" size="22" class="mr-2"></v-icon>
      <span>目录浏览</span>
    </div>

    <v-row class="mb-4">
      <v-col cols="12">
        <v-text-field
          v-model="searchKeyword"
          variant="outlined"
          hide-details
          placeholder="搜索文件/目录"
          prepend-inner-icon="mdi-magnify"
          class="search-field"
        ></v-text-field>
      </v-col>
    </v-row>
    <v-row class="mb-4">
      <v-col cols="12" sm="4" md="3">
        <v-btn
          color="primary"
          size="default"
          variant="flat"
          prepend-icon="mdi-download-multiple"
          :loading="batchStarting"
          :disabled="scrapingStatus.running"
          @click="scrapeCurrentDirectory"
          class="w-full"
        >
          刮削本目录
        </v-btn>
      </v-col>
      <v-col cols="12" sm="4" md="3">
        <v-btn
          color="info"
          size="default"
          variant="tonal"
          prepend-icon="mdi-bar-chart"
          :loading="scanningStats"
          @click="scanDirectoryStats"
          class="w-full"
        >
          扫描统计
        </v-btn>
      </v-col>
      <v-col cols="12" sm="4" md="3">
        <v-btn
          color="warning"
          size="default"
          variant="tonal"
          prepend-icon="mdi-trash-can"
          :loading="batchStarting"
          :disabled="scrapingStatus.running"
          @click="cleanCurrentDirectorySubtitles"
          class="w-full"
        >
          清理字幕
        </v-btn>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <div v-if="directoryContent" class="directory-content">
          <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-3"></v-progress-linear>

          <v-card v-if="scrapingStatus.running" class="section-card progress-card mb-4" elevation="0">
            <v-card-title class="section-title d-flex align-center">
              <v-icon icon="mdi-loader" color="primary" size="22" class="mr-2 animate-spin"></v-icon>
              正在刮削中
              <v-spacer></v-spacer>
              <v-btn
                color="error"
                size="default"
                variant="tonal"
                prepend-icon="mdi-stop"
                @click="abortScraping"
              >
                中止
              </v-btn>
            </v-card-title>
            <v-card-text>
              <v-progress-linear :value="scrapingStatus.total > 0 ? (scrapingStatus.processed / scrapingStatus.total * 100) : 0"
                                 color="primary" height="8" class="mb-3"></v-progress-linear>
              <div class="d-flex justify-between">
                <span class="text-body-1">当前文件: {{ scrapingStatus.current_file || '-' }}</span>
                <span class="text-body-1 font-weight-bold">{{ scrapingStatus.processed }} / {{ scrapingStatus.total }}</span>
              </div>
              <div class="d-flex justify-between mt-2">
                <span class="text-body-1">成功: <span class="text-success">{{ scrapingStatus.success }}</span> | 失败: <span class="text-error">{{ scrapingStatus.failed }}</span></span>
                <span class="text-body-1">耗时: {{ formatDuration(scrapingStatus.duration) }}</span>
              </div>
            </v-card-text>
          </v-card>

          <div v-if="currentPath"
               class="back-item d-flex align-center py-3 px-3 mb-3"
               @click="goBack()">
            <v-icon icon="mdi-keyboard-backspace" size="22" color="primary" class="mr-3"></v-icon>
            <span class="text-subtitle-1 text-primary cursor-pointer">
              {{ directoryContent.is_root ? '返回目录列表' : '返回上级目录' }}
            </span>
          </div>

          <template v-for="(item, index) in filteredItems" :key="index">
            <div v-if="item.type === 'directory'"
                 class="directory-item d-flex align-center py-3 px-3 mb-2"
                 @click="navigateToPath(item.path)">
              <v-icon icon="mdi-folder" size="22" color="primary" class="mr-3"></v-icon>
              <div class="flex-grow-1 d-flex align-center">
                <span class="text-body-1 cursor-pointer">{{ item.name }}</span>
                <v-chip
                  v-if="item.manual_match"
                  size="small"
                  color="secondary"
                  class="ml-2"
                  closable
                  @click.stop
                  @click:close.stop="clearManualMatch(item, item.manual_scope)"
                >
                  {{ manualChipText(item) }}
                </v-chip>
              </div>
              <div v-if="item.scrape_status" class="mr-3 text-right">
                <span class="text-body-1" :class="getScrapeStatusClass(item.scrape_status)">
                  {{ item.scrape_status.scraped_files }}/{{ item.scrape_status.total_files }}
                </span>
              </div>
              <v-btn
                icon="mdi-download-multiple"
                size="default"
                variant="text"
                color="primary"
                class="mr-1"
                :disabled="scrapingStatus.running"
                @click.stop="scrapeDirectory(item.path, true)"
              ></v-btn>
              <v-btn
                icon="mdi-magnify"
                size="default"
                variant="text"
                color="secondary"
                class="mr-1"
                @click.stop="openManualMatch(item)"
              ></v-btn>
              <v-icon icon="mdi-chevron-right" size="22" color="grey"></v-icon>
            </div>

            <div v-else-if="item.type === 'media'"
                 class="media-item d-flex align-center py-3 px-3 mb-2">
              <v-icon icon="mdi-video" size="22" color="info" class="mr-3"></v-icon>
              <div class="flex-grow-1">
                <div class="d-flex align-center flex-wrap">
                  <span class="text-body-1">{{ item.name }}</span>
                  <v-chip size="small" color="info" class="ml-2" v-if="item.danmu_count > 0">
                    弹幕: {{ item.danmu_count }}
                  </v-chip>
                  <v-chip size="small" color="grey" class="ml-2" v-else>
                    无弹幕
                  </v-chip>
                  <v-chip
                    v-if="item.manual_match"
                    size="small"
                    color="secondary"
                    class="ml-2"
                    closable
                    @click:close.stop="clearManualMatch(item, item.manual_scope)"
                  >
                    {{ manualChipText(item) }}
                  </v-chip>
                </div>
              </div>
              <v-btn
                color="secondary"
                size="default"
                variant="tonal"
                class="mr-2"
                @click="openManualMatch(item)"
              >
                <v-icon icon="mdi-magnify" size="20" class="mr-1"></v-icon>
                手动匹配
              </v-btn>
              <v-btn
                color="primary"
                size="default"
                variant="flat"
                :loading="item.generating"
                @click="generateDanmu(item)"
              >
                <v-icon icon="mdi-download" size="20" class="mr-1"></v-icon>
                刮削
              </v-btn>
            </div>
          </template>

          <div v-if="directoryContent.children && directoryContent.children.length === 0"
               class="text-center py-6">
            <v-alert type="info" variant="tonal" class="mb-2 text-body-1">
              该目录为空或没有支持的媒体文件
            </v-alert>
          </div>
        </div>

        <div v-else-if="loading" class="text-center py-6">
          <v-progress-linear indeterminate color="primary" class="mb-3"></v-progress-linear>
          <div class="text-body-1 text-grey">正在扫描目录，请稍候...</div>
        </div>

        <div v-else-if="notConfigured" class="text-center py-6">
          <v-alert type="info" variant="tonal" class="mb-2 text-body-1">
            请先在配置中设置刮削路径
          </v-alert>
        </div>

        <div v-else-if="error" class="text-center py-6">
          <v-alert type="error" variant="tonal" class="mb-2 text-body-1">{{ error }}</v-alert>
        </div>

        <div v-else class="text-center py-6">
          <v-alert type="info" variant="tonal" class="mb-2 text-body-1">
            请先在配置中设置刮削路径
          </v-alert>
        </div>
      </v-col>
    </v-row>

    <v-dialog v-model="manualDialog" max-width="720">
      <v-card class="section-card" elevation="0">
        <v-card-title class="section-title d-flex align-center">
          <v-icon icon="mdi-magnify" color="primary" size="22" class="mr-2"></v-icon>
          手动匹配弹幕
        </v-card-title>
        <v-card-text>
          <div class="text-body-1 text-grey mb-3">
            当前选择：{{ manualTargetItem?.name || '未选择文件' }}
          </div>
          <v-alert
            v-if="manualExistingMatch"
            type="info"
            variant="tonal"
            class="mb-3 text-body-1"
          >
            已匹配（{{ scopeLabel(manualExistingScope) }}）：{{ manualExistingMatch.animeTitle || `ID ${manualExistingMatch.animeId}` }}
            <span v-if="manualExistingOffset">（集数偏移 {{ formatOffset(manualExistingOffset) }}）</span>
          </v-alert>
          <v-alert
            v-if="manualSearchError"
            type="error"
            variant="tonal"
            class="mb-3 text-body-1"
            closable
            @click:close="manualSearchError = null"
          >
            {{ manualSearchError }}
          </v-alert>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="manualSearchKeyword"
                label="搜索关键字"
                variant="outlined"
                clearable
                hide-details
                @keyup.enter="performManualSearch"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-select
                v-model="manualSearchType"
                :items="manualTypeOptions"
                item-title="title"
                item-value="value"
                variant="outlined"
                hide-details
                label="类型"
              ></v-select>
            </v-col>
            <v-col cols="12" md="2" class="d-flex align-center">
              <v-btn
                color="primary"
                size="default"
                variant="flat"
                block
                :loading="manualSearchLoading"
                @click="performManualSearch"
              >
                搜索
              </v-btn>
            </v-col>
          </v-row>
          <v-progress-linear
            v-if="manualSearchLoading"
            indeterminate
            color="primary"
            class="mb-3 mt-2"
          ></v-progress-linear>
          <v-row v-if="manualTargetItem && manualTargetItem.type === 'media'">
            <v-col cols="12">
              <v-radio-group
                v-model="manualScope"
                inline
                hide-details
              >
                <v-radio label="仅当前文件" value="file"></v-radio>
                <v-radio label="整目录" value="directory"></v-radio>
              </v-radio-group>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="manualEpisodeOffset"
                label="集数偏移"
                type="number"
                variant="outlined"
                hint="本地集数 + 偏移 = 弹弹集数，如本地 13 对应弹弹 1 则填 -12"
                persistent-hint
              ></v-text-field>
            </v-col>
          </v-row>
          <v-alert
            v-if="!manualSearchLoading && manualSearchPerformed && manualSearchResults.length === 0"
            type="info"
            variant="tonal"
            class="mb-2 text-body-1"
          >
            未找到匹配结果，请调整关键字后再试。
          </v-alert>
          <v-list v-if="manualSearchResults.length > 0" lines="two" density="comfortable">
            <v-list-item
              v-for="anime in manualSearchResults"
              :key="anime.animeId"
              :active="manualSelected && manualSelected.animeId === anime.animeId"
              @click="selectManualResult(anime)"
            >
              <v-list-item-title class="text-body-1">{{ anime.animeTitle }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ anime.typeDescription || '未知类型' }}
                <span v-if="anime.episodeCount"> · {{ anime.episodeCount }} 集</span>
                <span v-if="anime.rating"> · 评分 {{ anime.rating }}</span>
                <span v-if="anime.startDate"> · {{ formatDate(anime.startDate) }}</span>
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon="mdi-check"
                  size="default"
                  variant="text"
                  :color="manualSelected && manualSelected.animeId === anime.animeId ? 'primary' : 'grey'"
                ></v-btn>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions class="px-6 py-4">
          <v-btn
            color="grey"
            variant="text"
            v-if="manualExistingMatch"
            @click="clearManualMatch(manualTargetItem, manualExistingScope || (manualTargetItem?.type === 'directory' ? 'directory' : 'file'), true)"
          >
            清除匹配
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="closeManualDialog">取消</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :disabled="!manualSelected"
            :loading="manualSaving"
            @click="confirmManualMatch"
          >
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="cleanConfirmDialog" max-width="500">
      <v-card class="section-card" elevation="0">
        <v-card-title class="section-title d-flex align-center">
          <v-icon icon="mdi-alert-circle" color="warning" size="22" class="mr-2"></v-icon>
          确认清理字幕
        </v-card-title>
        <v-card-text>
          <div class="text-body-1">
            确定要清理当前目录下的所有弹幕和合并字幕文件吗？
          </div>
          <div class="text-body-1 text-grey mt-3">
            目录：{{ currentPath }}
          </div>
          <v-alert
            type="warning"
            variant="tonal"
            class="mt-4 text-body-1"
          >
            此操作不可恢复，清理后需重新刮削获取弹幕。
          </v-alert>
        </v-card-text>
        <v-card-actions class="px-6 py-4">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="tonal" size="default" class="mr-3" @click="cleanConfirmDialog = false">取消</v-btn>
          <v-btn color="warning" variant="flat" size="default" @click="confirmCleanSubtitles">确认清理</v-btn>
          <v-spacer></v-spacer>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue';
import api from '../api';

const emit = defineEmits(['refresh']);

const error = ref(null);
const successMessage = ref(null);
const running = ref(false);
const batchStarting = ref(false);
let statusTimer = null;

const status = reactive({
  auto_scrape: false
});

const scrapingStatus = reactive({
  running: false,
  total: 0,
  processed: 0,
  success: 0,
  failed: 0,
  current_file: "",
  duration: 0
});

const directoryContent = ref(null);
const currentPath = ref('');
const loading = ref(false);
const notConfigured = ref(false);
const pathHistory = ref([]);

const searchKeyword = ref('');
const scanningStats = ref(false);

const manualDialog = ref(false);
const cleanConfirmDialog = ref(false);
const manualContext = ref(null);
const manualSearchKeyword = ref('');
const manualSearchType = ref('tvseries');
const manualTypeOptions = [
  { title: '全部类型', value: 'all' },
  { title: '电视剧', value: 'tvseries' },
  { title: '电影', value: 'movie' },
  { title: '动漫', value: 'ova' }
];
const manualSearchResults = ref([]);
const manualSearchLoading = ref(false);
const manualSearchError = ref(null);
const manualSearchPerformed = ref(false);
const manualSelected = ref(null);
const manualSaving = ref(false);
const manualScope = ref('directory');
const manualEpisodeOffset = ref(0);

const manualTargetItem = computed(() => manualContext.value?.item || null);
const manualExistingMatch = computed(() => manualTargetItem.value?.manual_match || null);
const manualExistingScope = computed(() => manualExistingMatch.value?.scope || null);
const manualExistingOffset = computed(() => Number(manualExistingMatch.value?.episodeOffset) || 0);

const filteredItems = computed(() => {
  if (!directoryContent.value || !directoryContent.value.children) {
    return [];
  }
  
  if (!searchKeyword.value) {
    return directoryContent.value.children;
  }
  
  const keyword = searchKeyword.value.toLowerCase();
  return directoryContent.value.children.filter(item => {
    return item.name.toLowerCase().includes(keyword);
  });
});

const getScrapeStatusClass = (scrapeStatus) => {
  if (!scrapeStatus || scrapeStatus.total_files === 0) {
    return 'text-grey';
  }
  if (scrapeStatus.scraped_files === scrapeStatus.total_files) {
    return 'text-success';
  }
  return 'text-warning';
};

function formatDuration(seconds) {
  if (!seconds) return '0秒';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  const parts = [];
  if (hours > 0) parts.push(`${hours}小时`);
  if (minutes > 0) parts.push(`${minutes}分钟`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}秒`);
  return parts.join('');
}

async function getStatus() {
  try {
    const res = await api.get('/status');
    const data = res && res.success ? res.data : null;
    if (data) {
      Object.assign(status, {
        auto_scrape: data.auto_scrape
      });

      Object.assign(scrapingStatus, {
        running: data.running,
        total: data.total,
        processed: data.processed,
        success: data.success,
        failed: data.failed,
        current_file: data.current_file,
        duration: data.duration
      });

      running.value = data.running;
    }
  } catch (err) {
    console.error('获取状态失败:', err);
    error.value = '获取状态失败，请检查网络或API';
  }
}

async function navigateToPath(path) {
  try {
    loading.value = true;
    error.value = null;
    notConfigured.value = false;
    searchKeyword.value = '';

    if (!path) {
      const data = await api.get('/scan_path');
      if (data && data.success) {
        directoryContent.value = data.data;
        currentPath.value = '';
        if (data.data.type === 'root') {
          pathHistory.value = [];
        }
      } else {
        const msg = data?.message || '';
        if (msg.includes('未配置')) {
          notConfigured.value = true;
        } else {
          error.value = msg || '加载根目录失败';
        }
      }
    } else {
      const data = await api.get('/scan_subfolder', {
        params: { subfolder_path: path }
      });
      
      if (data && data.success) {
        directoryContent.value = data.data;
        currentPath.value = path;
        
        if (!pathHistory.value.includes(path)) {
          pathHistory.value.push(path);
        }
      } else {
        error.value = data?.message || '加载目录失败';
      }
    }
  } catch (err) {
    console.error('导航失败:', err);
    error.value = '加载目录失败，请检查网络或API';
  } finally {
    loading.value = false;
  }
}

function goBack() {
  if (!currentPath.value) return;
  
  if (directoryContent.value?.is_root) {
    navigateToPath('');
  } else {
    const parentPath = currentPath.value.split('/').slice(0, -1).join('/');
    navigateToPath(parentPath || '');
  }
}

function closeManualDialog() {
  manualDialog.value = false;
  manualContext.value = null;
  manualSelected.value = null;
  manualScope.value = 'directory';
  manualEpisodeOffset.value = 0;
}

function formatOffset(offset) {
  return offset > 0 ? `+${offset}` : `${offset}`;
}

function scopeLabel(scope) {
  if (!scope) {
    return '目录';
  }
  if (scope === 'file') {
    return '单文件';
  }
  if (scope === 'directory') {
    return '目录';
  }
  return '未知';
}

function manualChipText(item) {
  if (!item?.manual_match) return '';
  const scopeText = item.manual_scope === 'file' ? '【单文件】' : '';
  const title = item.manual_match.animeTitle || `ID ${item.manual_match.animeId}`;
  const offset = Number(item.manual_match.episodeOffset) || 0;
  const offsetText = offset ? `（偏移${formatOffset(offset)}）` : '';
  return `${scopeText}${title}${offsetText}`;
}

function resolveDirectoryPath(item) {
  if (!item) return null;
  if (item.type === 'directory') {
    return item.path;
  }
  return item.directory_path || (item.path ? item.path.split('/').slice(0, -1).join('/') : null);
}

function sanitizeKeyword(name) {
  if (!name) return '';
  return name.replace(/\.[^/.]+$/, '').replace(/[\._]/g, ' ').trim();
}

function openManualMatch(item) {
  manualContext.value = { item };
  manualDialog.value = true;
  manualSearchError.value = null;
  manualSearchResults.value = [];
  manualSearchPerformed.value = false;
  manualSearchLoading.value = false;
  manualSaving.value = false;
  manualSelected.value = item.manual_match ? { ...item.manual_match } : null;
  manualEpisodeOffset.value = Number(item.manual_match?.episodeOffset) || 0;
  const existingScope = item.manual_scope || item.manual_match?.scope;
  if (item.type === 'directory') {
    manualScope.value = 'directory';
  } else if (existingScope === 'directory') {
    manualScope.value = 'directory';
  } else if (existingScope === 'file') {
    manualScope.value = 'file';
  } else {
    manualScope.value = 'file';
  }
  manualSearchKeyword.value = sanitizeKeyword(item.name) || manualSearchKeyword.value || '';
  manualSearchType.value = 'tvseries';
}

function selectManualResult(anime) {
  manualSelected.value = anime;
}

async function performManualSearch() {
  const keyword = manualSearchKeyword.value?.trim();
  if (!keyword) {
    manualSearchError.value = '请输入搜索关键字';
    manualSearchResults.value = [];
    manualSearchPerformed.value = true;
    return;
  }
  manualSearchLoading.value = true;
  manualSearchError.value = null;
  manualSearchPerformed.value = true;
  try {
    const params = {
      keyword,
    };
    if (manualSearchType.value && manualSearchType.value !== 'all') {
      params.type = manualSearchType.value;
    }
    const res = await api.get('/search_danmu', { params });
    if (res && res.success) {
      manualSearchResults.value = (res.data?.animes || []).slice(0, 50);
    } else {
      manualSearchResults.value = [];
      manualSearchError.value = res?.message || '搜索失败，请稍后重试';
    }
  } catch (err) {
    console.error('搜索弹弹失败:', err);
    manualSearchResults.value = [];
    manualSearchError.value = '搜索失败，请检查网络或API';
  } finally {
    manualSearchLoading.value = false;
  }
}

async function confirmManualMatch() {
  const targetItem = manualTargetItem.value;
  if (!targetItem || !manualSelected.value) {
    manualSearchError.value = '请选择一条匹配记录';
    return;
  }
  manualSaving.value = true;
  manualSearchError.value = null;
  try {
    const scope = manualScope.value;
    const directoryPath = scope === 'directory'
      ? resolveDirectoryPath(targetItem)
      : undefined;
    const offset = parseInt(manualEpisodeOffset.value, 10) || 0;
    const payload = {
      file_path: scope === 'file' ? targetItem.path : undefined,
      directory: directoryPath,
      scope,
      episodeOffset: offset,
      anime: manualSelected.value
    };
    const res = await api.post('/manual_match', payload);
    if (res && res.success) {
      successMessage.value = '手动匹配已保存';
      if (manualContext.value?.item) {
        manualContext.value.item.manual_match = res.data?.manual_match || manualSelected.value;
        manualContext.value.item.manual_scope = scope;
      }
      manualDialog.value = false;
      await navigateToPath(currentPath.value);
      emit('refresh');
    } else {
      manualSearchError.value = res?.message || '保存匹配失败';
    }
  } catch (err) {
    console.error('保存手动匹配失败:', err);
    manualSearchError.value = '保存失败，请检查网络或API';
  } finally {
    manualSaving.value = false;
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) {
    return (dateStr || '').split('T')[0] || dateStr;
  }
  return date.toISOString().split('T')[0];
}

async function scrapeDirectory(path, recursive = false) {
  if (!path) return;
  error.value = null;
  batchStarting.value = true;
  try {
    const params = { directory_path: path };
    if (recursive) {
      params.recursive = true;
    }
    const res = await api.get('/scrape_directory', { params });
    if (res && res.success) {
      successMessage.value = res.message || '已开始批量刮削';
      await getStatus();
      startStatusPolling();
    } else {
      error.value = res?.message || '启动批量刮削失败';
    }
  } catch (err) {
    console.error('启动批量刮削失败:', err);
    error.value = '启动批量刮削失败，请检查网络或API';
  } finally {
    batchStarting.value = false;
  }
}

function scrapeCurrentDirectory() {
  // 根层级时 currentPath 为空，实际路径在 directoryContent.path
  const target = currentPath.value || directoryContent.value?.path;
  if (!target) return;
  scrapeDirectory(target, false);
}

async function cleanCurrentDirectorySubtitles() {
  if (!currentPath.value) return;
  cleanConfirmDialog.value = true;
}

async function confirmCleanSubtitles() {
  cleanConfirmDialog.value = false;
  
  batchStarting.value = true;
  error.value = null;
  successMessage.value = null;
  
  try {
    const res = await api.get('/clean_subtitles', {
      params: { directory_path: currentPath.value }
    });
    
    if (res && res.success) {
      successMessage.value = `成功清理 ${res.data?.deleted?.length || 0} 个字幕文件`;
      await navigateToPath(currentPath.value);
      emit('refresh');
    } else {
      error.value = res?.message || '清理字幕失败';
    }
  } catch (err) {
    console.error('清理字幕失败:', err);
    error.value = '清理字幕失败，请检查网络或API';
  } finally {
    batchStarting.value = false;
  }
}

async function scanDirectoryStats() {
  if (!currentPath.value) return;
  
  scanningStats.value = true;
  
  try {
    const res = await api.get('/scan_directory_stats', {
      params: { directory_path: currentPath.value }
    });
    
    if (res && res.success) {
      successMessage.value = `扫描完成：共 ${res.data.total_files} 个视频文件，已刮削 ${res.data.scraped_files} 个`;
      await navigateToPath(currentPath.value);
      emit('refresh');
    } else {
      error.value = res?.message || '扫描统计失败';
    }
  } catch (err) {
    console.error('扫描统计失败:', err);
    error.value = '扫描统计失败，请检查网络或API';
  } finally {
    scanningStats.value = false;
  }
}

async function abortScraping() {
  try {
    const res = await api.get('/abort_scrape');
    if (res && res.success) {
      successMessage.value = '已发送中止请求';
    } else {
      error.value = res?.message || '中止失败';
    }
  } catch (err) {
    console.error('中止失败:', err);
    error.value = '中止失败，请检查网络或API';
  }
}

function startStatusPolling() {
  if (statusTimer) return;
  statusTimer = setInterval(async () => {
    await getStatus();
    if (!scrapingStatus.running) {
      stopStatusPolling();
      const { success, failed, total } = scrapingStatus;
      successMessage.value = `批量刮削完成：成功 ${success}，失败 ${failed}，共 ${total}`;
      // 全局通知：不论是否切换页面都弹出
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: {
          success: failed === 0,
          title: failed === 0 ? '批量刮削完成' : '批量刮削完成（存在失败）',
          text: `共 ${total} 个文件，成功 ${success}，失败 ${failed}`,
        },
      }));
      await navigateToPath(currentPath.value);
      emit('refresh');
    }
  }, 3000);
}

function stopStatusPolling() {
  if (statusTimer) {
    clearInterval(statusTimer);
    statusTimer = null;
  }
}

async function generateDanmu(item) {
  error.value = null;
  try {
    item.generating = true;
    const result = await api.get('/generate_danmu', {
      params: { file_path: item.path }
    });
    if (result && result.success) {
      successMessage.value = '弹幕生成成功';
      const count = result.data?.danmu_count ?? 0;
      const name = result.data?.file_name || item.name;
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: { success: true, title: '弹幕生成成功', text: `${name}（${count} 条）` },
      }));
      await navigateToPath(currentPath.value);
      emit('refresh');
    } else {
      console.log('后端返回：', result);
      const msg = result?.message || '弹幕生成失败';
      error.value = msg;
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: { success: false, title: '弹幕生成失败', text: msg },
      }));
    }
  } catch (err) {
    error.value = '生成弹幕失败，请检查网络或API';
    window.dispatchEvent(new CustomEvent('app:notify', {
      detail: { success: false, title: '弹幕生成失败', text: '请检查网络或API' },
    }));
  } finally {
    item.generating = false;
  }
}

async function clearManualMatch(item, scopeOverride = null, keepDialog = false) {
  if (!item) {
    return;
  }
  manualSearchError.value = null;
  try {
    const scope = (scopeOverride || item?.manual_scope || (item?.type === 'directory' ? 'directory' : 'file'));
    const params = { scope };
    if (scope === 'file') {
      params.file_path = item.path;
    } else {
      params.directory = resolveDirectoryPath(item);
      if (!params.directory) {
        manualSearchError.value = '未能确定需要移除的目录';
        return;
      }
    }
    const res = await api.get('/remove_manual_match', { params });
    if (res && res.success) {
      successMessage.value = '已移除手动匹配';
      if (manualContext.value?.item?.path === item.path) {
        manualContext.value.item.manual_match = null;
        manualContext.value.item.manual_scope = null;
        manualSelected.value = null;
        if (keepDialog && manualTargetItem.value?.type === 'media') {
          manualScope.value = 'file';
        }
        if (!keepDialog) {
          manualDialog.value = false;
        }
      }
      await navigateToPath(currentPath.value);
      emit('refresh');
    } else {
      manualSearchError.value = res?.message || '移除手动匹配失败';
    }
  } catch (err) {
    console.error('移除手动匹配失败:', err);
    manualSearchError.value = '移除手动匹配失败，请检查网络或API';
  }
}

onMounted(async () => {
  await Promise.all([getStatus(), navigateToPath('')]);
  if (scrapingStatus.running) {
    startStatusPolling();
  }
});

onUnmounted(() => {
  stopStatusPolling();
});
</script>

<style scoped>
.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.87);
}

.section-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #FFFFFF;
  transition: box-shadow 0.2s ease;
}

.section-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.section-card :deep(.v-card-title) {
  padding: 1rem 1.25rem 0.5rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.section-card :deep(.v-card-text) {
  padding: 1.25rem;
}

.progress-card {
  background: linear-gradient(135deg, rgba(25, 118, 210, 0.05), rgba(25, 118, 210, 0.01));
}

.directory-content {
  max-height: calc(100vh - 350px);
  min-height: 300px;
  overflow-y: auto;
}

.directory-item {
  border-radius: 10px;
  transition: background-color 0.2s ease;
  cursor: pointer;
}

.directory-item:hover {
  background-color: rgba(25, 118, 210, 0.05);
}

.back-item {
  border-radius: 10px;
  transition: all 0.2s ease;
  cursor: pointer;
  border: 1px dashed rgba(25, 118, 210, 0.3);
  background-color: rgba(25, 118, 210, 0.02);
}

.back-item:hover {
  background-color: rgba(25, 118, 210, 0.06);
  border-color: rgba(25, 118, 210, 0.5);
}

.media-item {
  border-radius: 10px;
  transition: background-color 0.2s ease;
}

.media-item:hover {
  background-color: rgba(0, 0, 0, 0.025);
}

.cursor-pointer {
  cursor: pointer;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
