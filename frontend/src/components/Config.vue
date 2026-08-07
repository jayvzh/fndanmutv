<template>
  <div class="plugin-config">
    <v-card flat class="rounded border">
      <!-- 标题区域 -->
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2 bg-primary-lighten-5">
        <v-icon icon="mdi-cog" class="mr-2" color="primary" size="small" />
        <span>DanmuTV 弹幕刮削配置</span>
      </v-card-title>
      
      <v-card-text class="px-3 py-2">
        <!-- 插件说明 -->
        <v-card flat class="rounded mb-3 border config-card">
          <v-card-text class="d-flex align-center px-3 py-2">
            <v-icon icon="mdi-information" color="info" class="mr-2" size="small"></v-icon>
            <span class="text-body-2">
              用于生成影视弹幕字幕文件，支持电视剧、电影、动漫等多种媒体类型。弹幕来源为自定义弹幕 API 后端。
            </span>
          </v-card-text>
        </v-card>
        
        <v-alert v-if="error" type="error" density="compact" class="mb-2 text-caption" variant="tonal" closable>{{ error }}</v-alert>
        <v-alert v-if="successMessage" type="success" density="compact" class="mb-2 text-caption" variant="tonal" closable>{{ successMessage }}</v-alert>

        <v-form ref="form" v-model="isFormValid" @submit.prevent="saveFullConfig">
          <!-- 基本设置卡片 -->
          <v-card flat class="rounded mb-3 border config-card">
            <v-card-title class="text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5">
              <v-icon icon="mdi-tune" class="mr-2" color="primary" size="small" />
              <span>基本设置</span>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-power" size="small" :color="editableConfig.enable ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用插件</div>
                          <div class="text-caption text-grey">是否启用弹幕刮削功能</div>
                        </div>
                        <v-switch
                          v-model="editableConfig.enable"
                          color="primary"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-auto-fix" size="small" :color="editableConfig.auto_scrape ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">入库自动刮削</div>
                          <div class="text-caption text-grey">是否在媒体入库时自动刮削弹幕</div>
                        </div>
                        <v-switch
                          v-model="editableConfig.auto_scrape"
                          color="success"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-play-speed" size="small" :color="editableConfig.auto_scrape_on_start ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启动时立即扫描一次</div>
                          <div class="text-caption text-grey">应用启动后立即执行一次自动扫描</div>
                        </div>
                        <v-switch
                          v-model="editableConfig.auto_scrape_on_start"
                          color="success"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="editableConfig.auto_scrape_interval"
                    label="自动扫描间隔(秒)"
                    type="number"
                    variant="outlined"
                    :min="0"
                    hint="设为 0 可禁用定时扫描"
                    persistent-hint
                    prepend-inner-icon="mdi-timer"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-repeat" size="small" :color="editableConfig.enable_retry_task ? 'warning' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用重试任务</div>
                          <div class="text-caption text-grey">弹幕数量不足时自动加入重试列表</div>
                        </div>
                        <v-switch
                          v-model="editableConfig.enable_retry_task"
                          color="warning"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-history" size="small" :color="editableConfig.enable_history_details ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">记录历史详情</div>
                          <div class="text-caption text-grey">记录批量刮削时每个文件的处理详情</div>
                        </div>
                        <v-switch
                          v-model="editableConfig.enable_history_details"
                          color="info"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-file-video-outline" size="small" :color="editableConfig.enable_strm ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div class="d-flex align-center">
                          <div>
                            <div class="text-subtitle-2">启用 STRM 文件刮削</div>
                            <div class="text-caption text-grey">是否支持 .strm 流媒体文件的弹幕刮削</div>
                          </div>
                          <v-tooltip location="top">
                            <template v-slot:activator="{ props: tipProps }">
                              <v-btn
                                v-bind="tipProps"
                                icon="mdi-help-circle-outline"
                                size="x-small"
                                variant="text"
                                color="grey"
                                class="ml-2"
                              ></v-btn>
                            </template>
                            <div class="tooltip-content">
                              <div class="text-subtitle-2 mb-1">STRM 文件刮削说明</div>
                              <div class="text-caption">
                                <div class="mb-1"><strong>功能限制：</strong></div>
                                <div>• 仅支持 TMDB ID 匹配，无法使用文件 hash</div>
                                <div>• 无法提取内嵌字幕，仅支持外部字幕</div>
                                <div>• 使用默认分辨率 (1920x1080)</div>
                              </div>
                            </div>
                          </v-tooltip>
                        </div>
                        <v-switch
                          v-model="editableConfig.enable_strm"
                          color="info"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12">
                  <div class="d-flex align-center flex-row ga-2">
                    <v-text-field
                      v-model="editableConfig.danmu_api_url"
                      label="弹幕 API 地址"
                      variant="outlined"
                      placeholder="http://danmu-api:9321"
                      hint="弹幕 API 后端地址（容器内推荐 http://danmu-api:9321）"
                      persistent-hint
                      prepend-inner-icon="mdi-web"
                      :disabled="saving || testingApi"
                      density="compact"
                      class="text-caption api-url-field"
                    ></v-text-field>
                    <v-btn
                      color="primary"
                      variant="tonal"
                      size="small"
                      :loading="testingApi"
                      :disabled="saving || testingApi || !editableConfig.danmu_api_url"
                      @click="testApiConnection"
                      prepend-icon="mdi-connection"
                    >
                      测试连接
                    </v-btn>
                  </div>
                  <v-alert v-if="apiTestResult" :type="apiTestResult.ok ? 'success' : 'error'" density="compact" variant="tonal" class="mt-1 text-caption" closable @click:close="apiTestResult = null">
                    {{ apiTestResult.message }}
                  </v-alert>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 弹幕参数设置 -->
          <v-card flat class="rounded mb-3 border config-card">
            <v-card-title class="text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5">
              <v-icon icon="mdi-video" class="mr-2" color="primary" size="small" />
              <span>弹幕参数设置</span>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="editableConfig.fontsize"
                    label="字体大小"
                    type="number"
                    variant="outlined"
                    :min="1"
                    :rules="[v => v > 0 || '字体大小必须大于0']"
                    hint="弹幕字体大小"
                    persistent-hint
                    prepend-inner-icon="mdi-format-font-size-increase"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="editableConfig.screen_area"
                    label="弹幕显示区域"
                    variant="outlined"
                    :items="[
                      { title: '全屏弹幕', value: 'full' },
                      { title: '半屏弹幕', value: 'half' },
                      { title: '1/3屏弹幕', value: 'third' },
                      { title: '1/4屏弹幕', value: 'quarter' }
                    ]"
                    hint="选择弹幕显示的屏幕区域，超出区域的弹幕将被忽略"
                    persistent-hint
                    prepend-inner-icon="mdi-monitor"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="editableConfig.alpha"
                    label="透明度"
                    type="number"
                    variant="outlined"
                    :min="0"
                    :max="1"
                    :step="0.1"
                    :rules="[v => v >= 0 && v <= 1 || '透明度必须在0-1之间']"
                    hint="弹幕透明度(0-1)"
                    persistent-hint
                    prepend-inner-icon="mdi-opacity"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="editableConfig.duration"
                    label="持续时间"
                    type="number"
                    variant="outlined"
                    :min="1"
                    :rules="[v => v > 0 || '持续时间必须大于0']"
                    hint="弹幕显示持续时间(秒)"
                    persistent-hint
                    prepend-inner-icon="mdi-clock-outline"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-layers" size="small" :color="editableConfig.enable_multi_layer ? 'primary' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用多层弹幕</div>
                          <div class="text-caption text-grey">开启后弹幕分层显示，具有不同速度和透明度，营造深度感</div>
                        </div>
                        <v-switch
                          v-model="editableConfig.enable_multi_layer"
                          color="primary"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                      <div v-if="editableConfig.enable_multi_layer" class="d-flex align-center mt-2">
                        <div class="text-caption text-grey mr-3">弹幕层数</div>
                        <v-btn-toggle
                          v-model.number="editableConfig.multi_layer_count"
                          mandatory
                          density="compact"
                          color="primary"
                          :disabled="saving"
                        >
                          <v-btn :value="2" size="small">2层</v-btn>
                          <v-btn :value="3" size="small">3层</v-btn>
                        </v-btn-toggle>
                        <div class="text-caption text-grey ml-3">
                          <span v-if="editableConfig.multi_layer_count === 2">顶层15% / 中层85%</span>
                          <span v-else>顶层20% / 中层60% / 底层20%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-format-vertical-align-top" size="small" :color="editableConfig.random_top_bottom ? 'primary' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">随机顶/底部弹幕</div>
                          <div class="text-caption text-grey">从滚动弹幕中随机分配比例转为悬停弹幕（最大10%）</div>
                        </div>
                        <v-switch
                          v-model="editableConfig.random_top_bottom"
                          color="primary"
                          inset
                          :disabled="saving"
                          density="compact"
                          hide-details
                          class="small-switch"
                        ></v-switch>
                      </div>
                      <div v-if="editableConfig.random_top_bottom" class="d-flex align-center mt-2" style="gap: 12px;">
                        <v-text-field
                          v-model.number="editableConfig.top_ratio"
                          label="顶部比例"
                          type="number"
                          density="compact"
                          variant="outlined"
                          hide-details
                          :min="0"
                          :max="10"
                          :step="1"
                          suffix="%"
                          style="max-width: 130px;"
                          :disabled="saving"
                        ></v-text-field>
                        <v-text-field
                          v-model.number="editableConfig.bottom_ratio"
                          label="底部比例"
                          type="number"
                          density="compact"
                          variant="outlined"
                          hide-details
                          :min="0"
                          :max="10"
                          :step="1"
                          suffix="%"
                          style="max-width: 130px;"
                          :disabled="saving"
                        ></v-text-field>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-chart-bell-curve" size="small" color="grey" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">弹幕密度</div>
                          <div class="text-caption text-grey">随机保留指定比例的弹幕，降低可减少拥挤（100%为全部保留）</div>
                        </div>
                        <v-text-field
                          v-model.number="editableConfig.density"
                          type="number"
                          density="compact"
                          variant="outlined"
                          hide-details
                          :min="10"
                          :max="100"
                          :step="5"
                          suffix="%"
                          style="max-width: 130px;"
                          :disabled="saving"
                        ></v-text-field>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-arrow-expand-horizontal" size="small" color="grey" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">弹幕宽度扩展</div>
                          <div class="text-caption text-grey">扩大弹幕显示区域宽度，解决超宽屏/手机屏左右空白问题</div>
                        </div>
                        <v-select
                          v-model.number="editableConfig.width_scale"
                          density="compact"
                          variant="outlined"
                          hide-details
                          :items="[
                            { title: '1.0x (标准)', value: 1.0 },
                            { title: '1.1x', value: 1.1 },
                            { title: '1.2x', value: 1.2 },
                            { title: '1.3x', value: 1.3 },
                            { title: '1.4x', value: 1.4 },
                            { title: '1.5x', value: 1.5 },
                            { title: '1.6x', value: 1.6 },
                            { title: '1.7x', value: 1.7 },
                            { title: '1.8x', value: 1.8 },
                            { title: '1.9x', value: 1.9 },
                            { title: '2.0x', value: 2.0 }
                          ]"
                          item-title="title"
                          item-value="value"
                          style="max-width: 150px;"
                          :disabled="saving"
                        ></v-select>
                      </div>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 刮削路径设置 -->
          <v-card flat class="rounded mb-3 border config-card">
            <v-card-title class="text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5">
              <v-icon icon="mdi-folder" class="mr-2" color="primary" size="small" />
              <span>手动控制媒体库路径</span>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-textarea
                v-model="editableConfig.path"
                label="/"
                variant="outlined"
                hint="每行一个路径,在状态页手动控制刮削"
                persistent-hint
                prepend-inner-icon="mdi-folder-multiple"
                :disabled="saving"
                density="compact"
                class="text-caption"
                rows="3"
              ></v-textarea>
            </v-card-text>
          </v-card>
        </v-form>
      </v-card-text>
      
      <v-divider></v-divider>
      
      <v-card-actions class="px-2 py-1">
        <v-btn color="info" @click="emit('switch')" prepend-icon="mdi-view-dashboard" :disabled="saving" variant="text" size="small">状态页</v-btn>
        <v-spacer></v-spacer>
        <v-btn color="secondary" variant="text" @click="resetConfigToFetched" :disabled="!initialConfigLoaded || saving" prepend-icon="mdi-restore" size="small">重置</v-btn>
        <v-btn color="primary" :disabled="!isFormValid || saving" @click="saveFullConfig" :loading="saving" prepend-icon="mdi-content-save" variant="text" size="small">保存配置</v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '../api';

const emit = defineEmits(['switch']);

const form = ref(null);
const isFormValid = ref(true);
const error = ref(null);
const successMessage = ref(null);
const saving = ref(false);
const testingApi = ref(false);
const apiTestResult = ref(null);
const initialConfigLoaded = ref(false);

const defaultConfig = () => ({
  enable: false,
  width: 1920,
  height: 1080,
  fontsize: 48,
  alpha: 0.7,
  duration: 14,
  path: '',
  auto_scrape: true,
  auto_scrape_on_start: false,
  auto_scrape_interval: 3600,
  enable_retry_task: true,
  screen_area: 'quarter',
  enable_strm: true,
  danmu_api_url: 'http://danmu-api:9321',
  enable_multi_layer: false,
  multi_layer_count: 2,
  random_top_bottom: false,
  top_ratio: 0,
  bottom_ratio: 0,
  density: 100,
  width_scale: 1.0,
});

// Holds the config as fetched from server, used for reset
const serverFetchedConfig = reactive({});

// Holds the config being edited in the form
const editableConfig = reactive(defaultConfig());

const toEditable = (data) => ({
  enable: data?.enabled ?? false,
  width: data?.width ?? 1920,
  height: data?.height ?? 1080,
  fontsize: data?.fontsize ?? 48,
  alpha: data?.alpha ?? 0.7,
  duration: data?.duration ?? 14,
  path: data?.path ?? '',
  auto_scrape: data?.auto_scrape ?? true,
  auto_scrape_on_start: data?.auto_scrape_on_start ?? false,
  auto_scrape_interval: data?.auto_scrape_interval ?? 3600,
  enable_retry_task: data?.enable_retry_task ?? true,
  screen_area: data?.screen_area ?? 'quarter',
  enable_strm: data?.enable_strm ?? true,
  danmu_api_url: data?.danmu_api_url || 'http://danmu-api:9321',
  enable_multi_layer: data?.enable_multi_layer ?? false,
  multi_layer_count: data?.multi_layer_count ?? 2,
  random_top_bottom: data?.random_top_bottom ?? false,
  top_ratio: data?.top_ratio ?? 0,
  bottom_ratio: data?.bottom_ratio ?? 0,
  density: data?.density ?? 100,
  width_scale: data?.width_scale ?? 1.0,
});

async function loadInitialData() {
  error.value = null;
  saving.value = true;
  initialConfigLoaded.value = false;

  try {
    const data = await api.get('/config');
    if (data) {
      Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(data)));
      Object.assign(editableConfig, toEditable(data));
      initialConfigLoaded.value = true;
      successMessage.value = '成功加载配置';
    } else {
      throw new Error('加载配置失败');
    }
  } catch (err) {
    console.error('加载配置失败:', err);
    error.value = err?.response?.data?.detail || err.message || '加载配置失败，请检查网络或 API';
    successMessage.value = null;
  } finally {
    saving.value = false;
    setTimeout(() => { successMessage.value = null; error.value = null; }, 4000);
  }
}

async function testApiConnection() {
  if (!editableConfig.danmu_api_url) return;
  testingApi.value = true;
  apiTestResult.value = null;
  try {
    const res = await api.get('/api_status', { api_url: editableConfig.danmu_api_url });
    if (res && res.success) {
      apiTestResult.value = { ok: true, message: res.message || 'API 连接成功' };
    } else {
      apiTestResult.value = { ok: false, message: res?.message || 'API 连接失败' };
    }
  } catch (err) {
    apiTestResult.value = { ok: false, message: err?.message || 'API 检测请求失败' };
  } finally {
    testingApi.value = false;
    setTimeout(() => { if (apiTestResult.value?.ok) apiTestResult.value = null; }, 5000);
  }
}

async function saveFullConfig() {
  error.value = null;
  successMessage.value = null;
  if (!form.value) return;

  const validation = await form.value.validate();
  if (!validation.valid) {
    error.value = '请检查表单中的错误';
    return;
  }

  saving.value = true;

  try {
    const configToSave = {
      enabled: editableConfig.enable,
      width: editableConfig.width,
      height: editableConfig.height,
      fontsize: editableConfig.fontsize,
      alpha: editableConfig.alpha,
      duration: editableConfig.duration,
      path: editableConfig.path,
      auto_scrape: editableConfig.auto_scrape,
      auto_scrape_on_start: editableConfig.auto_scrape_on_start,
      auto_scrape_interval: editableConfig.auto_scrape_interval,
      enable_retry_task: editableConfig.enable_retry_task,
      screen_area: editableConfig.screen_area,
      enable_strm: editableConfig.enable_strm,
      danmu_api_url: editableConfig.danmu_api_url,
      enable_multi_layer: editableConfig.enable_multi_layer,
      multi_layer_count: editableConfig.multi_layer_count,
      random_top_bottom: editableConfig.random_top_bottom,
      top_ratio: editableConfig.top_ratio,
      bottom_ratio: editableConfig.bottom_ratio,
      density: editableConfig.density,
      width_scale: editableConfig.width_scale,
    };

    const res = await api.post('/config', configToSave);
    if (res && res.success === false) {
      throw new Error(res.message || '保存配置失败');
    }

    Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(configToSave)));
    successMessage.value = '配置已保存';
  } catch (err) {
    console.error('保存配置失败:', err);
    error.value = err?.response?.data?.detail || err.message || '保存配置失败，请检查网络或查看日志';
  } finally {
    saving.value = false;
    setTimeout(() => {
      successMessage.value = null;
      if (error.value && !error.value.startsWith('保存配置失败')) {
        error.value = null;
      }
    }, 5000);
  }
}

function resetConfigToFetched() {
  if (initialConfigLoaded.value) {
    Object.assign(editableConfig, toEditable(serverFetchedConfig));
    error.value = null;
    successMessage.value = '配置已重置为上次加载的状态';
    if (form.value) form.value.resetValidation();
  } else {
    error.value = '重置失败';
  }
  setTimeout(() => { successMessage.value = null; error.value = null; }, 3000);
}

onMounted(() => {
  loadInitialData();
});
</script>

<style scoped>
.plugin-config {
  max-width: 80rem;
  margin: 0 auto;
  padding: 0.5rem;
}

.bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.07);
}

.border {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.config-card {
  background-image: linear-gradient(to right, rgba(var(--v-theme-surface), 0.98), rgba(var(--v-theme-surface), 0.95)), 
                    repeating-linear-gradient(45deg, rgba(var(--v-theme-primary), 0.03), rgba(var(--v-theme-primary), 0.03) 10px, transparent 10px, transparent 20px);
  background-attachment: fixed;
  box-shadow: 0 1px 2px rgba(var(--v-border-color), 0.05) !important;
  transition: all 0.3s ease;
}

.config-card:hover {
  box-shadow: 0 3px 6px rgba(var(--v-border-color), 0.1) !important;
}

.setting-item {
  border-radius: 8px;
  transition: all 0.2s ease;
  padding: 0.5rem;
  margin-bottom: 4px;
}

.setting-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.03);
}

.small-switch {
  transform: scale(0.8);
  margin-right: -8px;
}

.text-subtitle-2 {
  font-size: 14px !important;
  font-weight: 500;
  margin-bottom: 2px;
}

.tooltip-content {
  max-width: 350px;
  padding: 4px;
  line-height: 1.4;
}

.tooltip-content .text-caption {
  color: rgba(255, 255, 255, 0.87);
}

.tooltip-content strong {
  color: rgba(255, 255, 255, 0.95);
}

.tooltip-content div {
  margin-bottom: 2px;
}

.api-url-field {
  flex: 0 0 60%;
  max-width: 60%;
}
</style>
