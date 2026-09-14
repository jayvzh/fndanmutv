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
          rounded="lg"
          placeholder="搜索文件/目录"
          prepend-inner-icon="mdi-magnify"
          class="search-field"
        ></v-text-field>
      </v-col>
    </v-row>
    <div class="d-flex flex-wrap ga-2 mb-4 browse-toolbar">
      <v-btn
        color="primary"
        variant="flat"
        prepend-icon="mdi-download-multiple"
        :loading="batchStarting"
        :disabled="scrapingStatus.running"
        @click="scrapeCurrentDirectory"
      >
        <span class="d-none d-sm-inline">刮削本目录</span><span class="d-sm-none">刮削</span>
      </v-btn>
      <v-btn
        color="info"
        variant="tonal"
        prepend-icon="mdi-clipboard-list-outline"
        class="tonal-bordered"
        :loading="scanningStats"
        :disabled="scanningStats"
        @click="scanDirectoryStats"
      >
        <span class="d-none d-sm-inline">{{ currentPath ? '扫描统计' : '扫描统计全部库' }}</span><span class="d-sm-none">扫描</span>
      </v-btn>
      <v-btn
        color="warning"
        variant="tonal"
        prepend-icon="mdi-broom"
        class="tonal-bordered"
        :loading="batchStarting"
        :disabled="scrapingStatus.running"
        @click="cleanCurrentDirectorySubtitles"
      >
        <span class="d-none d-sm-inline">清理字幕</span><span class="d-sm-none">清理</span>
      </v-btn>
      <!-- 移动端换行点：刷新/排序独占一行 -->
      <div class="toolbar-break" aria-hidden="true"></div>
      <v-btn
        color="primary"
        variant="tonal"
        prepend-icon="mdi-refresh"
        class="tonal-bordered"
        @click="refreshCurrentDir"
      >
        刷新
      </v-btn>
      <v-menu :menu-props="{ contentClass: 'sort-menu-content' }">
        <template #activator="{ props }">
          <v-btn
            color="primary"
            variant="tonal"
            prepend-icon="mdi-sort"
            :append-icon="sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down'"
            class="tonal-bordered ml-auto browse-sort-btn"
            v-bind="props"
          >
            排序
          </v-btn>
        </template>
        <v-list density="comfortable">
          <v-list-item
            v-for="opt in sortOptions"
            :key="opt.key"
            :active="sortBy === opt.field && sortDir === opt.dir"
            @click="selectSort(opt)"
          >
            <template #prepend>
              <v-icon
                :icon="sortBy === opt.field && sortDir === opt.dir ? 'mdi-check' : 'mdi-check-blank'"
                size="18"
              ></v-icon>
            </template>
            <v-list-item-title class="text-body-2">{{ opt.label }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </div>

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
              {{ directoryContent.is_root ? '返回媒体库列表' : '返回上级目录' }}
            </span>
          </div>

          <template v-for="(item, index) in pagedItems" :key="index">
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
              <div v-else-if="statsLoading" class="mr-3 d-flex">
                <v-progress-circular indeterminate size="16" width="2" color="grey"></v-progress-circular>
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

        <div v-if="directoryContent && totalPages > 1"
             class="d-flex align-center justify-center flex-wrap ga-3 mt-2">
          <span class="text-body-2 text-grey">{{ pageRange }} 共 {{ filteredItems.length }}</span>
          <v-pagination
            v-model="currentPage"
            :length="totalPages"
            :total-visible="7"
            rounded
            density="comfortable"
          ></v-pagination>
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
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue';
import api from '../api';
import {
  BROWSE_CACHE_KEY,
  BROWSE_LAST_PATH_KEY,
  BROWSE_CACHE_TTL_MS,
  readCache,
  writeCache,
} from '../utils/cache';

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

// 目录缓存持久化到 localStorage：切 tab / 刷新页面不丢失；
// 条目超过 BROWSE_CACHE_TTL_MS 后视为过期，下次访问自动重新拉取
const browseStore = readCache(BROWSE_CACHE_KEY) || { dirs: {}, stats: {} };
const dirCache = browseStore.dirs; // cacheKey -> { content, currentPath, isRoot, ts }

function persistBrowse() {
  // 只保留最近 30 个目录条目，防止无限增长
  const entries = Object.entries(dirCache)
    .sort((a, b) => (b[1].ts || 0) - (a[1].ts || 0));
  for (const [key] of entries.slice(30)) {
    delete dirCache[key];
  }
  browseStore.stats = Object.fromEntries(statsCache);
  writeCache(BROWSE_CACHE_KEY, browseStore);
}

const searchKeyword = ref('');
const scanningStats = ref(false);

// 排序：目录组在前、文件组在后，两组分别应用同一排序；默认修改时间新→旧
const sortBy = ref('mtime'); // 'name' | 'natural' | 'mtime'
const sortDir = ref('desc'); // 'asc' | 'desc'
const sortOptions = [
  { key: 'name-asc', field: 'name', dir: 'asc', label: '文件名 正序' },
  { key: 'name-desc', field: 'name', dir: 'desc', label: '文件名 倒序' },
  { key: 'natural-asc', field: 'natural', dir: 'asc', label: '自然排序 正序' },
  { key: 'natural-desc', field: 'natural', dir: 'desc', label: '自然排序 倒序' },
  { key: 'mtime-desc', field: 'mtime', dir: 'desc', label: '修改时间 新→旧' },
  { key: 'mtime-asc', field: 'mtime', dir: 'asc', label: '修改时间 旧→新' },
];
function selectSort(opt) {
  sortBy.value = opt.field;
  sortDir.value = opt.dir;
}

// 分页：每页 20 项；目录的视频/弹幕数量需向后端递归统计，仅对当前页可见目录懒加载
const PAGE_SIZE = 20;
const currentPage = ref(1);
const statsLoading = ref(false);
const statsCache = new Map();   // path -> {total_files, scraped_files}，随目录缓存一并持久化
const statsInflight = new Set();

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

const compareByName = (a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0);

const compareItems = (a, b) => {
  let r = 0;
  if (sortBy.value === 'mtime') {
    // mtime 缺失（旧缓存/取不到）排最后
    const am = a.mtime ?? -Infinity;
    const bm = b.mtime ?? -Infinity;
    r = am - bm;
  } else if (sortBy.value === 'natural') {
    r = a.name.localeCompare(b.name, undefined, { numeric: true });
  } else {
    r = compareByName(a, b);
  }
  return sortDir.value === 'asc' ? r : -r;
};

const filteredItems = computed(() => {
  const children = directoryContent.value?.children;
  if (!children) {
    return [];
  }

  // filter 产生新数组，sort 不会影响原 children（缓存）顺序
  const dirs = children.filter((item) => item.type === 'directory').sort(compareItems);
  const files = children.filter((item) => item.type !== 'directory').sort(compareItems);
  const items = [...dirs, ...files];

  if (!searchKeyword.value) {
    return items;
  }

  const keyword = searchKeyword.value.toLowerCase();
  return items.filter((item) => item.name.toLowerCase().includes(keyword));
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / PAGE_SIZE)));

// 与 data-table footer 一致的「1-7 共 23」格式
const pageRange = computed(() => {
  const total = filteredItems.value.length;
  const start = total === 0 ? 0 : (currentPage.value - 1) * PAGE_SIZE + 1;
  const end = Math.min(currentPage.value * PAGE_SIZE, total);
  return `${start}-${end}`;
});

const pagedItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return filteredItems.value.slice(start, start + PAGE_SIZE);
});

// 仅为当前页可见的目录项请求递归统计（未显示的不往下钻）
async function ensureVisibleStats() {
  const children = directoryContent.value?.children;
  if (!children) return;
  // 先回填已有缓存
  for (const item of pagedItems.value) {
    if (item.type === 'directory' && item.scrape_status == null && statsCache.has(item.path)) {
      item.scrape_status = statsCache.get(item.path);
    }
  }
  const targets = pagedItems.value.filter(
    (item) => item.type === 'directory' && item.scrape_status == null && !statsInflight.has(item.path)
  );
  if (!targets.length) return;
  targets.forEach((item) => statsInflight.add(item.path));
  statsLoading.value = true;
  try {
    const res = await api.get('/directory_stats', {
      params: { path: targets.map((item) => item.path).join('\n') }
    });
    if (res?.success) {
      const stats = res.data?.stats || {};
      for (const item of targets) {
        const s = stats[item.path] || { total_files: 0, scraped_files: 0 };
        statsCache.set(item.path, s);
        const child = children.find((c) => c.path === item.path);
        if (child) child.scrape_status = s;
      }
      persistBrowse();
    }
  } catch (err) {
    console.error('加载目录统计失败:', err);
  } finally {
    targets.forEach((item) => statsInflight.delete(item.path));
    statsLoading.value = false;
  }
}

watch(searchKeyword, () => {
  currentPage.value = 1;
});

watch([sortBy, sortDir], () => {
  currentPage.value = 1;
});

watch(pagedItems, () => {
  ensureVisibleStats();
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

async function navigateToPath(path, force = false) {
  try {
    loading.value = true;
    error.value = null;
    notConfigured.value = false;
    searchKeyword.value = '';
    currentPage.value = 1;
    // 强制刷新（刮削/清理/扫描统计后）丢弃懒加载缓存，让统计重新下钻
    if (force) {
      statsCache.clear();
      persistBrowse();
    }

    const cacheKey = path || '__root__';
    const cached = !force ? dirCache[cacheKey] : null;
    if (cached && Date.now() - (cached.ts || 0) <= BROWSE_CACHE_TTL_MS) {
      directoryContent.value = cached.content;
      currentPath.value = cached.currentPath;
      if (pathHistory.value.length === 0 && cached.isRoot) {
        pathHistory.value = [];
      }
      return;
    }
    if (cached) {
      delete dirCache[cacheKey]; // 过期条目丢弃，走重新拉取
    }

    if (!path) {
      const data = await api.get('/scan_path', { params: { include_child_stats: false } });
      if (data && data.success) {
        directoryContent.value = data.data;
        currentPath.value = '';
        dirCache[cacheKey] = {
          content: data.data,
          currentPath: '',
          isRoot: data.data.type === 'root',
          ts: Date.now()
        };
        persistBrowse();
        writeCache(BROWSE_LAST_PATH_KEY, '');
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
        params: { subfolder_path: path, include_child_stats: false }
      });
      
      if (data && data.success) {
        directoryContent.value = data.data;
        currentPath.value = path;
        dirCache[cacheKey] = {
          content: data.data,
          currentPath: path,
          isRoot: false,
          ts: Date.now()
        };
        persistBrowse();
        writeCache(BROWSE_LAST_PATH_KEY, path);
        
        if (!pathHistory.value.includes(path)) {
          pathHistory.value.push(path);
        }
      } else {
        error.value = data?.message || '加载目录失败';
        // 越界路径（如旧版“返回上级”残留的 lastPath）自动回退媒体库列表
        if (path && (data?.message || '').includes('媒体库')) {
          error.value = null;
          await navigateToPath('');
        }
      }
    }
  } catch (err) {
    console.error('导航失败:', err);
    error.value = '加载目录失败，请检查网络或API';
  } finally {
    loading.value = false;
  }
}

function refreshCurrentDir() {
  const cacheKey = currentPath.value || '__root__';
  delete dirCache[cacheKey];
  persistBrowse();
  navigateToPath(currentPath.value, true);
}

// 媒体库根路径列表：来自根视图缓存（多库 = 各库目录；单库 = 库根本身）
function getLibraryRoots() {
  const rootContent = dirCache['__root__']?.content;
  if (!rootContent) return [];
  if (rootContent.type === 'root') {
    return (rootContent.children || []).map((c) => c.path).filter(Boolean);
  }
  return rootContent.path ? [rootContent.path] : [];
}

function goBack() {
  if (!currentPath.value) return;

  if (directoryContent.value?.is_root) {
    navigateToPath('');
  } else {
    const parentPath = currentPath.value.split('/').slice(0, -1).join('/');
    const roots = getLibraryRoots();
    // 父路径不在媒体库范围内时直接回媒体库列表（后端同样会拒绝越界路径）
    const within = roots.length === 0
      || roots.some((root) => parentPath === root || parentPath.startsWith(`${root}/`));
    navigateToPath(within ? parentPath : '');
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
  // 搜索前清除关键字中的空白字符与中英文括号
  const keyword = (manualSearchKeyword.value || '')
    .replace(/\s+/g, '')
    .replace(/[()（）]/g, '')
    .trim();
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
      await navigateToPath(currentPath.value, true);
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
      await navigateToPath(currentPath.value, true);
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
  if (scanningStats.value) return;

  scanningStats.value = true;
  error.value = null;
  // 立即反馈：根目录扫全部媒体库，子目录只扫当前目录
  successMessage.value = currentPath.value
    ? '正在扫描统计当前目录，媒体库较大时可能较慢…'
    : '正在扫描统计所有媒体库，较大时可能需要数分钟…';

  try {
    const res = await api.get('/scan_directory_stats', {
      params: currentPath.value ? { directory_path: currentPath.value } : {},
      timeout: 600000,
    });

    if (res && res.success) {
      const d = res.data || {};
      successMessage.value = d.libraries != null
        ? `扫描完成：${d.libraries} 个媒体库，共 ${d.total_files} 个视频文件，已刮削 ${d.scraped_files} 个`
        : `扫描完成：共 ${d.total_files} 个视频文件，已刮削 ${d.scraped_files} 个`;
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: { success: true, title: '扫描统计完成', text: successMessage.value },
      }));
      await navigateToPath(currentPath.value, true);
      emit('refresh');
    } else {
      error.value = res?.message || '扫描统计失败';
      window.dispatchEvent(new CustomEvent('app:notify', {
        detail: { success: false, title: '扫描统计失败', text: error.value },
      }));
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
          type: failed === 0 ? 'success' : 'warning',
          title: failed === 0 ? '批量刮削完成' : '批量刮削完成（存在失败）',
          text: `共 ${total} 个文件，成功 ${success}，失败 ${failed}`,
        },
      }));
      await navigateToPath(currentPath.value, true);
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
      await navigateToPath(currentPath.value, true);
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
      await navigateToPath(currentPath.value, true);
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
  // 恢复上次浏览的目录：命中缓存直接展示（未过期），过期或无缓存时自动重新拉取
  const lastPath = readCache(BROWSE_LAST_PATH_KEY) || '';
  await Promise.all([getStatus(), navigateToPath(lastPath)]);
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

/* tonal 按钮加同色边框：tonal 的文字色即主题色，currentColor 让边框自动匹配 info/warning/primary */
.v-btn.tonal-bordered {
  border: 1px solid currentColor;
}

.section-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  background: #FFFFFF;
  transition: box-shadow 0.2s ease;
}

/* 弹窗内 v-card 被 Vuetify 规则（.v-dialog > .v-overlay__content > .v-card，4px）覆盖，
   这里提高特异性保证弹窗卡片同为 16px 圆角 */
.v-dialog .section-card.section-card {
  border-radius: 16px;
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

.toolbar-break {
  display: none;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 移动端（<600px）：前三个按钮一行居中，刷新/排序换行一行居中 */
@media (max-width: 599.98px) {
  .browse-toolbar {
    justify-content: center;
  }

  .toolbar-break {
    display: block;
    flex: 1 1 100%;
  }

  .browse-sort-btn {
    margin-left: 0 !important;
  }
}
</style>

<style>
/* 排序下拉菜单：大圆角（菜单内容 teleport 到 body，需全局样式） */
.sort-menu-content {
  border-radius: 18px;
  overflow: hidden;
}
</style>
