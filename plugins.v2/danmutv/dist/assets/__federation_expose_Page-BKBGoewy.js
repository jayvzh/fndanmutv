import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const {resolveComponent:_resolveComponent$5,createVNode:_createVNode$5,createTextVNode:_createTextVNode$5,withCtx:_withCtx$5,createElementVNode:_createElementVNode$5,toDisplayString:_toDisplayString$4,normalizeClass:_normalizeClass$1,openBlock:_openBlock$5,createElementBlock:_createElementBlock$5,createCommentVNode:_createCommentVNode$5,createBlock:_createBlock$5} = await importShared('vue');


const _hoisted_1$5 = { class: "status-item d-flex align-center py-2" };
const _hoisted_2$4 = { class: "status-content flex-grow-1" };
const _hoisted_3$4 = { class: "status-item d-flex align-center py-2" };
const _hoisted_4$4 = { class: "status-content flex-grow-1" };
const _hoisted_5$3 = { class: "status-item d-flex align-center py-2" };
const _hoisted_6$3 = { class: "status-content flex-grow-1" };
const _hoisted_7$2 = { class: "stat-item text-center py-2" };
const _hoisted_8$2 = { class: "text-h6 font-weight-bold text-primary" };
const _hoisted_9$2 = { class: "stat-item text-center py-2" };
const _hoisted_10$2 = { class: "text-h6 font-weight-bold text-success" };
const _hoisted_11$1 = { class: "stat-item text-center py-2" };
const _hoisted_12$1 = { class: "text-h6 font-weight-bold text-error" };
const _hoisted_13$1 = { class: "stat-item text-center py-2" };
const _hoisted_14$1 = { class: "text-h6 font-weight-bold text-warning" };
const _hoisted_15$1 = { class: "d-flex align-center justify-space-between py-2" };
const _hoisted_16$1 = { class: "d-flex align-center" };
const _hoisted_17$1 = {
  key: 0,
  class: "text-body-2 font-weight-bold text-primary"
};
const _hoisted_18$1 = {
  key: 1,
  class: "text-body-2 text-grey"
};
const _hoisted_19$1 = { class: "d-flex align-center justify-space-between py-2" };
const _hoisted_20$1 = { class: "d-flex align-center" };
const _hoisted_21$1 = {
  key: 0,
  class: "text-body-2 font-weight-bold text-warning"
};
const _hoisted_22$1 = {
  key: 1,
  class: "text-body-2 text-grey"
};
const _hoisted_23$1 = { class: "flex justify-between mt-2" };
const _hoisted_24$1 = { class: "flex justify-between" };

const {ref: ref$5,onMounted: onMounted$4,onUnmounted: onUnmounted$1} = await importShared('vue');



const _sfc_main$5 = {
  __name: 'Dashboard',
  props: {
  api: { 
    type: [Object, Function],
    required: true,
  }
},
  setup(__props) {

const props = __props;

const enabled = ref$5(false);
const apiConnected = ref$5(false);
const apiMessage = ref$5('');
const mediaLibraryAccessible = ref$5(false);
const mediaLibraryCount = ref$5(0);
const stats = ref$5({ total_files: 0, success_count: 0, failed_count: 0, retry_tasks_count: 0 });
const nextRetryTime = ref$5(null);
const lastRun = ref$5(null);
const scrapingStatus = ref$5({ running: false, total: 0, processed: 0, success: 0, failed: 0, current_file: null, duration: 0 });

let refreshInterval = null;

const fetchStatus = async () => {
  try {
    const data = await props.api.get('plugin/DanmuTV/full_status');
    if (data && data.success) {
      const result = data.data;
      enabled.value = result.enabled;
      apiConnected.value = result.api_connected;
      apiMessage.value = result.api_message;
      mediaLibraryAccessible.value = result.media_library_accessible;
      mediaLibraryCount.value = result.media_library_count || 0;
      stats.value = result.stats;
      nextRetryTime.value = result.next_retry_time;
      lastRun.value = result.last_run;
      scrapingStatus.value = {
        running: result.running,
        total: result.total,
        processed: result.processed,
        success: result.success,
        failed: result.failed,
        current_file: result.current_file,
        duration: result.duration
      };
    }
  } catch (error) {
    console.error('获取状态失败:', error);
  }
};

const triggerRetry = async () => {
  try {
    await props.api.get('plugin/DanmuTV/process_retry_tasks');
    await fetchStatus();
  } catch (error) {
    console.error('触发重试失败:', error);
  }
};

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
};

const formatDuration = (seconds) => {
  if (!seconds) return '0秒'
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`
};

const getTypeLabel = (type) => {
  const labels = { 'batch': '批量刮削', 'single': '单文件刮削', 'retry': '重试任务' };
  return labels[type] || type
};

onMounted$4(() => {
  fetchStatus();
  refreshInterval = setInterval(fetchStatus, 5000);
});

onUnmounted$1(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$5("v-icon");
  const _component_v_card_title = _resolveComponent$5("v-card-title");
  const _component_v_col = _resolveComponent$5("v-col");
  const _component_v_row = _resolveComponent$5("v-row");
  const _component_v_card_text = _resolveComponent$5("v-card-text");
  const _component_v_card = _resolveComponent$5("v-card");
  const _component_v_chip = _resolveComponent$5("v-chip");
  const _component_v_btn = _resolveComponent$5("v-btn");
  const _component_v_progress_linear = _resolveComponent$5("v-progress-linear");
  const _component_v_container = _resolveComponent$5("v-container");

  return (_openBlock$5(), _createBlock$5(_component_v_container, {
    fluid: "",
    class: "pa-4"
  }, {
    default: _withCtx$5(() => [
      _createVNode$5(_component_v_row, { class: "mb-4" }, {
        default: _withCtx$5(() => [
          _createVNode$5(_component_v_col, { cols: "12" }, {
            default: _withCtx$5(() => [
              _createVNode$5(_component_v_card, { class: "status-card" }, {
                default: _withCtx$5(() => [
                  _createVNode$5(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
                    default: _withCtx$5(() => [
                      _createVNode$5(_component_v_icon, {
                        icon: "mdi-information",
                        color: "primary",
                        size: "small",
                        class: "mr-2"
                      }),
                      _cache[0] || (_cache[0] = _createTextVNode$5(" 插件状态 ", -1))
                    ]),
                    _: 1
                  }),
                  _createVNode$5(_component_v_card_text, { class: "px-3 py-2" }, {
                    default: _withCtx$5(() => [
                      _createVNode$5(_component_v_row, null, {
                        default: _withCtx$5(() => [
                          _createVNode$5(_component_v_col, {
                            cols: "12",
                            sm: "4"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_1$5, [
                                _createVNode$5(_component_v_icon, {
                                  icon: enabled.value ? 'mdi-check-circle' : 'mdi-close-circle',
                                  color: enabled.value ? 'success' : 'error',
                                  size: "small",
                                  class: "mr-3"
                                }, null, 8, ["icon", "color"]),
                                _createElementVNode$5("div", _hoisted_2$4, [
                                  _cache[1] || (_cache[1] = _createElementVNode$5("div", { class: "text-subtitle-2" }, "插件启用", -1)),
                                  _createElementVNode$5("div", {
                                    class: _normalizeClass$1(["text-caption", enabled.value ? 'text-success' : 'text-error'])
                                  }, _toDisplayString$4(enabled.value ? '已启用' : '未启用'), 3)
                                ])
                              ])
                            ]),
                            _: 1
                          }),
                          _createVNode$5(_component_v_col, {
                            cols: "12",
                            sm: "4"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_3$4, [
                                _createVNode$5(_component_v_icon, {
                                  icon: apiConnected.value ? 'mdi-web' : 'mdi-web-off',
                                  color: apiConnected.value ? 'success' : 'error',
                                  size: "small",
                                  class: "mr-3"
                                }, null, 8, ["icon", "color"]),
                                _createElementVNode$5("div", _hoisted_4$4, [
                                  _cache[2] || (_cache[2] = _createElementVNode$5("div", { class: "text-subtitle-2" }, "API状态", -1)),
                                  _createElementVNode$5("div", {
                                    class: _normalizeClass$1(["text-caption", apiConnected.value ? 'text-success' : 'text-error'])
                                  }, _toDisplayString$4(apiConnected.value ? '正常' : '异常'), 3)
                                ])
                              ])
                            ]),
                            _: 1
                          }),
                          _createVNode$5(_component_v_col, {
                            cols: "12",
                            sm: "4"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_5$3, [
                                _createVNode$5(_component_v_icon, {
                                  icon: mediaLibraryAccessible.value ? 'mdi-folder-check' : 'mdi-folder-alert',
                                  color: mediaLibraryAccessible.value ? 'success' : 'error',
                                  size: "small",
                                  class: "mr-3"
                                }, null, 8, ["icon", "color"]),
                                _createElementVNode$5("div", _hoisted_6$3, [
                                  _cache[3] || (_cache[3] = _createElementVNode$5("div", { class: "text-subtitle-2" }, "媒体库", -1)),
                                  _createElementVNode$5("div", {
                                    class: _normalizeClass$1(["text-caption", mediaLibraryAccessible.value ? 'text-success' : 'text-error'])
                                  }, _toDisplayString$4(mediaLibraryAccessible.value ? `可访问 (${mediaLibraryCount.value})` : '不可访问'), 3)
                                ])
                              ])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode$5(_component_v_row, { class: "mb-4" }, {
        default: _withCtx$5(() => [
          _createVNode$5(_component_v_col, { cols: "12" }, {
            default: _withCtx$5(() => [
              _createVNode$5(_component_v_card, {
                flat: "",
                class: "rounded border"
              }, {
                default: _withCtx$5(() => [
                  _createVNode$5(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
                    default: _withCtx$5(() => [
                      _createVNode$5(_component_v_icon, {
                        icon: "mdi-chart-bar",
                        color: "primary",
                        size: "small",
                        class: "mr-2"
                      }),
                      _cache[4] || (_cache[4] = _createTextVNode$5(" 统计信息 ", -1))
                    ]),
                    _: 1
                  }),
                  _createVNode$5(_component_v_card_text, { class: "px-3 py-2" }, {
                    default: _withCtx$5(() => [
                      _createVNode$5(_component_v_row, null, {
                        default: _withCtx$5(() => [
                          _createVNode$5(_component_v_col, {
                            cols: "6",
                            sm: "3"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_7$2, [
                                _createElementVNode$5("div", _hoisted_8$2, _toDisplayString$4(stats.value.total_files), 1),
                                _cache[5] || (_cache[5] = _createElementVNode$5("div", { class: "text-caption text-grey mt-1" }, "媒体库文件", -1))
                              ])
                            ]),
                            _: 1
                          }),
                          _createVNode$5(_component_v_col, {
                            cols: "6",
                            sm: "3"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_9$2, [
                                _createElementVNode$5("div", _hoisted_10$2, _toDisplayString$4(stats.value.success_count), 1),
                                _cache[6] || (_cache[6] = _createElementVNode$5("div", { class: "text-caption text-grey mt-1" }, "已刮削", -1))
                              ])
                            ]),
                            _: 1
                          }),
                          _createVNode$5(_component_v_col, {
                            cols: "6",
                            sm: "3"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_11$1, [
                                _createElementVNode$5("div", _hoisted_12$1, _toDisplayString$4(stats.value.failed_count), 1),
                                _cache[7] || (_cache[7] = _createElementVNode$5("div", { class: "text-caption text-grey mt-1" }, "失败", -1))
                              ])
                            ]),
                            _: 1
                          }),
                          _createVNode$5(_component_v_col, {
                            cols: "6",
                            sm: "3"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_13$1, [
                                _createElementVNode$5("div", _hoisted_14$1, _toDisplayString$4(stats.value.retry_tasks_count), 1),
                                _cache[8] || (_cache[8] = _createElementVNode$5("div", { class: "text-caption text-grey mt-1" }, "待重试", -1))
                              ])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode$5(_component_v_row, { class: "mb-4" }, {
        default: _withCtx$5(() => [
          _createVNode$5(_component_v_col, { cols: "12" }, {
            default: _withCtx$5(() => [
              _createVNode$5(_component_v_card, {
                flat: "",
                class: "rounded border"
              }, {
                default: _withCtx$5(() => [
                  _createVNode$5(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
                    default: _withCtx$5(() => [
                      _createVNode$5(_component_v_icon, {
                        icon: "mdi-history",
                        color: "primary",
                        size: "small",
                        class: "mr-2"
                      }),
                      _cache[9] || (_cache[9] = _createTextVNode$5(" 最近运行 ", -1))
                    ]),
                    _: 1
                  }),
                  _createVNode$5(_component_v_card_text, { class: "px-3 py-3" }, {
                    default: _withCtx$5(() => [
                      _createVNode$5(_component_v_row, null, {
                        default: _withCtx$5(() => [
                          _createVNode$5(_component_v_col, {
                            cols: "12",
                            sm: "6"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_15$1, [
                                _createElementVNode$5("div", _hoisted_16$1, [
                                  _createVNode$5(_component_v_icon, {
                                    icon: "mdi-clock-outline",
                                    size: "small",
                                    color: "primary",
                                    class: "mr-2"
                                  }),
                                  _cache[10] || (_cache[10] = _createElementVNode$5("span", { class: "text-body-2" }, "最近运行时间", -1))
                                ]),
                                (lastRun.value)
                                  ? (_openBlock$5(), _createElementBlock$5("div", _hoisted_17$1, [
                                      _createTextVNode$5(_toDisplayString$4(formatTime(lastRun.value.timestamp)) + " ", 1),
                                      _createVNode$5(_component_v_chip, {
                                        size: "x-small",
                                        color: "primary",
                                        variant: "tonal",
                                        class: "ml-2"
                                      }, {
                                        default: _withCtx$5(() => [
                                          _createTextVNode$5(_toDisplayString$4(getTypeLabel(lastRun.value.type)), 1)
                                        ]),
                                        _: 1
                                      })
                                    ]))
                                  : (_openBlock$5(), _createElementBlock$5("span", _hoisted_18$1, "暂无记录"))
                              ])
                            ]),
                            _: 1
                          }),
                          _createVNode$5(_component_v_col, {
                            cols: "12",
                            sm: "6"
                          }, {
                            default: _withCtx$5(() => [
                              _createElementVNode$5("div", _hoisted_19$1, [
                                _createElementVNode$5("div", _hoisted_20$1, [
                                  _createVNode$5(_component_v_icon, {
                                    icon: "mdi-calendar-clock",
                                    size: "small",
                                    color: "warning",
                                    class: "mr-2"
                                  }),
                                  _cache[11] || (_cache[11] = _createElementVNode$5("span", { class: "text-body-2" }, "下次运行时间", -1))
                                ]),
                                (nextRetryTime.value)
                                  ? (_openBlock$5(), _createElementBlock$5("div", _hoisted_21$1, [
                                      _createTextVNode$5(_toDisplayString$4(nextRetryTime.value) + " ", 1),
                                      _createVNode$5(_component_v_chip, {
                                        size: "x-small",
                                        color: "warning",
                                        variant: "tonal",
                                        class: "ml-2"
                                      }, {
                                        default: _withCtx$5(() => [...(_cache[12] || (_cache[12] = [
                                          _createTextVNode$5("单个重试", -1)
                                        ]))]),
                                        _: 1
                                      })
                                    ]))
                                  : (_openBlock$5(), _createElementBlock$5("span", _hoisted_22$1, "暂无重试任务"))
                              ])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }),
                      (lastRun.value)
                        ? (_openBlock$5(), _createBlock$5(_component_v_row, {
                            key: 0,
                            class: "mt-2"
                          }, {
                            default: _withCtx$5(() => [
                              _createVNode$5(_component_v_col, { cols: "12" }, {
                                default: _withCtx$5(() => [
                                  _createVNode$5(_component_v_btn, {
                                    color: "primary",
                                    size: "small",
                                    variant: "tonal",
                                    onClick: triggerRetry,
                                    disabled: !stats.value.retry_tasks_count
                                  }, {
                                    default: _withCtx$5(() => [
                                      _createVNode$5(_component_v_icon, {
                                        icon: "mdi-refresh",
                                        class: "mr-1"
                                      }),
                                      _createTextVNode$5(" 立即重试 (" + _toDisplayString$4(stats.value.retry_tasks_count) + ") ", 1)
                                    ]),
                                    _: 1
                                  }, 8, ["disabled"])
                                ]),
                                _: 1
                              })
                            ]),
                            _: 1
                          }))
                        : _createCommentVNode$5("", true)
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      (scrapingStatus.value.running)
        ? (_openBlock$5(), _createBlock$5(_component_v_row, { key: 0 }, {
            default: _withCtx$5(() => [
              _createVNode$5(_component_v_col, { cols: "12" }, {
                default: _withCtx$5(() => [
                  _createVNode$5(_component_v_card, { class: "bg-primary-lighten-5" }, {
                    default: _withCtx$5(() => [
                      _createVNode$5(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2" }, {
                        default: _withCtx$5(() => [
                          _createVNode$5(_component_v_icon, {
                            icon: "mdi-loader",
                            color: "primary",
                            size: "small",
                            class: "mr-2 animate-spin"
                          }),
                          _cache[13] || (_cache[13] = _createTextVNode$5(" 正在刮削中 ", -1))
                        ]),
                        _: 1
                      }),
                      _createVNode$5(_component_v_card_text, { class: "px-3 py-2" }, {
                        default: _withCtx$5(() => [
                          _createVNode$5(_component_v_progress_linear, {
                            value: scrapingStatus.value.total > 0 ? (scrapingStatus.value.processed / scrapingStatus.value.total * 100) : 0,
                            color: "primary",
                            height: "8"
                          }, null, 8, ["value"]),
                          _createElementVNode$5("div", _hoisted_23$1, [
                            _createElementVNode$5("span", null, "当前文件: " + _toDisplayString$4(scrapingStatus.value.current_file), 1),
                            _createElementVNode$5("span", null, _toDisplayString$4(scrapingStatus.value.processed) + " / " + _toDisplayString$4(scrapingStatus.value.total), 1)
                          ]),
                          _createElementVNode$5("div", _hoisted_24$1, [
                            _createElementVNode$5("span", null, "成功: " + _toDisplayString$4(scrapingStatus.value.success) + " | 失败: " + _toDisplayString$4(scrapingStatus.value.failed), 1),
                            _createElementVNode$5("span", null, "耗时: " + _toDisplayString$4(formatDuration(scrapingStatus.value.duration)), 1)
                          ])
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          }))
        : _createCommentVNode$5("", true)
    ]),
    _: 1
  }))
}
}

};
const Dashboard = /*#__PURE__*/_export_sfc(_sfc_main$5, [['__scopeId',"data-v-81dd44fc"]]);

const {resolveComponent:_resolveComponent$4,createVNode:_createVNode$4,createElementVNode:_createElementVNode$4,createTextVNode:_createTextVNode$4,withCtx:_withCtx$4,toDisplayString:_toDisplayString$3,openBlock:_openBlock$4,createBlock:_createBlock$4,createCommentVNode:_createCommentVNode$4,createElementBlock:_createElementBlock$4,renderList:_renderList,Fragment:_Fragment,withModifiers:_withModifiers,normalizeClass:_normalizeClass,withKeys:_withKeys} = await importShared('vue');


const _hoisted_1$4 = {
  key: 0,
  class: "directory-content"
};
const _hoisted_2$3 = { class: "flex justify-between" };
const _hoisted_3$3 = { class: "text-body-2" };
const _hoisted_4$3 = { class: "text-body-2 font-bold" };
const _hoisted_5$2 = { class: "flex justify-between mt-1" };
const _hoisted_6$2 = { class: "text-body-2" };
const _hoisted_7$1 = { class: "text-success" };
const _hoisted_8$1 = { class: "text-error" };
const _hoisted_9$1 = { class: "text-body-2" };
const _hoisted_10$1 = { class: "text-subtitle-2 text-primary cursor-pointer" };
const _hoisted_11 = ["onClick"];
const _hoisted_12 = { class: "flex-grow-1 d-flex align-center" };
const _hoisted_13 = { class: "text-subtitle-2 cursor-pointer" };
const _hoisted_14 = {
  key: 0,
  class: "mr-2 text-right"
};
const _hoisted_15 = {
  key: 1,
  class: "media-item d-flex align-center py-2"
};
const _hoisted_16 = { class: "flex-grow-1" };
const _hoisted_17 = { class: "d-flex align-center" };
const _hoisted_18 = { class: "text-subtitle-2" };
const _hoisted_19 = {
  key: 3,
  class: "text-center py-4"
};
const _hoisted_20 = {
  key: 1,
  class: "text-center py-4"
};
const _hoisted_21 = {
  key: 2,
  class: "text-center py-4"
};
const _hoisted_22 = {
  key: 3,
  class: "text-center py-4"
};
const _hoisted_23 = {
  key: 4,
  class: "text-center py-4"
};
const _hoisted_24 = { class: "text-caption text-grey mb-2" };
const _hoisted_25 = { key: 0 };
const _hoisted_26 = { key: 0 };
const _hoisted_27 = { key: 1 };
const _hoisted_28 = { key: 2 };
const _hoisted_29 = { class: "text-caption text-grey mt-2" };

const {ref: ref$4,reactive: reactive$1,onMounted: onMounted$3,onUnmounted,computed: computed$1} = await importShared('vue');



const _sfc_main$4 = {
  __name: 'BrowseView',
  props: {
  api: { 
    type: [Object, Function],
    required: true,
  }
},
  emits: ['refresh'],
  setup(__props, { emit: __emit }) {

const props = __props;

const emit = __emit;

const error = ref$4(null);
const successMessage = ref$4(null);
const running = ref$4(false);
const batchStarting = ref$4(false);
let statusTimer = null;

const status = reactive$1({
  enabled: false
});

const scrapingStatus = reactive$1({
  running: false,
  total: 0,
  processed: 0,
  success: 0,
  failed: 0,
  current_file: "",
  duration: 0
});

const directoryContent = ref$4(null);
const currentPath = ref$4('');
const loading = ref$4(false);
const notConfigured = ref$4(false);
const pathHistory = ref$4([]);

// 目录缓存: { path: data }
const dirCache = new Map();

const searchKeyword = ref$4('');
const scanningStats = ref$4(false);

const manualDialog = ref$4(false);
const cleanConfirmDialog = ref$4(false);
const manualContext = ref$4(null);
const manualSearchKeyword = ref$4('');
const manualSearchType = ref$4('tvseries');
const manualTypeOptions = [
  { title: '全部类型', value: 'all' },
  { title: '电视剧', value: 'tvseries' },
  { title: '电影', value: 'movie' },
  { title: '动漫', value: 'ova' }
];
const manualSearchResults = ref$4([]);
const manualSearchLoading = ref$4(false);
const manualSearchError = ref$4(null);
const manualSearchPerformed = ref$4(false);
const manualSelected = ref$4(null);
const manualSaving = ref$4(false);
const manualScope = ref$4('directory');
const manualEpisodeOffset = ref$4(0);

const manualTargetItem = computed$1(() => manualContext.value?.item || null);
const manualExistingMatch = computed$1(() => manualTargetItem.value?.manual_match || null);
const manualExistingScope = computed$1(() => manualExistingMatch.value?.scope || null);
const manualExistingOffset = computed$1(() => Number(manualExistingMatch.value?.episodeOffset) || 0);

const filteredItems = computed$1(() => {
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
    const data = await props.api.get('plugin/DanmuTV/status');
    if (data) {
      Object.assign(status, {
        enabled: data.enabled
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
  // 有缓存且非强制刷新时直接使用缓存
  const cacheKey = path || '';
  if (!force && dirCache.has(cacheKey)) {
    directoryContent.value = dirCache.get(cacheKey);
    currentPath.value = path || '';
    searchKeyword.value = '';
    return;
  }

  try {
    loading.value = true;
    error.value = null;
    notConfigured.value = false;
    searchKeyword.value = '';

    if (!path) {
      const data = await props.api.get('plugin/DanmuTV/scan_path');
      if (data && data.success) {
        directoryContent.value = data.data;
        currentPath.value = '';
        dirCache.set('', data.data);
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
      const data = await props.api.get('plugin/DanmuTV/scan_subfolder', {
        params: { subfolder_path: path }
      });
      
      if (data && data.success) {
        directoryContent.value = data.data;
        currentPath.value = path;
        dirCache.set(path, data.data);
        
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

function refreshCurrentDir() {
  dirCache.delete(currentPath.value || '');
  navigateToPath(currentPath.value, true);
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
    const res = await props.api.get('plugin/DanmuTV/search_danmu', { params });
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
    const res = await props.api.post('plugin/DanmuTV/manual_match', payload);
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
    const res = await props.api.get('plugin/DanmuTV/scrape_directory', { params });
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
  scrapeDirectory(currentPath.value, false);
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
    const res = await props.api.get('plugin/DanmuTV/clean_subtitles', {
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
  if (!currentPath.value) return;
  
  scanningStats.value = true;
  
  try {
    const res = await props.api.get('plugin/DanmuTV/scan_directory_stats', {
      params: { directory_path: currentPath.value }
    });
    
    if (res && res.success) {
      successMessage.value = `扫描完成：共 ${res.data.total_files} 个视频文件，已刮削 ${res.data.scraped_files} 个`;
      await navigateToPath(currentPath.value, true);
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
    const res = await props.api.get('plugin/DanmuTV/abort_scrape');
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
      successMessage.value = `批量刮削完成：成功 ${scrapingStatus.success}，失败 ${scrapingStatus.failed}，共 ${scrapingStatus.total}`;
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
    const result = await props.api.get('plugin/DanmuTV/generate_danmu', {
      params: { file_path: item.path }
    });
    if (result && result.success) {
      successMessage.value = `弹幕生成成功（${result.data?.danmu_count || 0}条）`;
      await navigateToPath(currentPath.value, true);
      emit('refresh');
    } else {
      error.value = result?.message || '弹幕生成失败';
      // 刷新目录以更新弹幕状态，同时通知历史记录更新
      await navigateToPath(currentPath.value, true);
      emit('refresh');
    }
  } catch (err) {
    error.value = '生成弹幕失败，请检查网络或API';
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
    const res = await props.api.get('plugin/DanmuTV/remove_manual_match', { params });
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

onMounted$3(async () => {
  await Promise.all([getStatus(), navigateToPath('')]);
  if (scrapingStatus.running) {
    startStatusPolling();
  }
});

onUnmounted(() => {
  stopStatusPolling();
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$4("v-icon");
  const _component_v_spacer = _resolveComponent$4("v-spacer");
  const _component_v_btn = _resolveComponent$4("v-btn");
  const _component_v_card_title = _resolveComponent$4("v-card-title");
  const _component_v_alert = _resolveComponent$4("v-alert");
  const _component_v_text_field = _resolveComponent$4("v-text-field");
  const _component_v_col = _resolveComponent$4("v-col");
  const _component_v_row = _resolveComponent$4("v-row");
  const _component_v_progress_linear = _resolveComponent$4("v-progress-linear");
  const _component_v_card_text = _resolveComponent$4("v-card-text");
  const _component_v_card = _resolveComponent$4("v-card");
  const _component_v_chip = _resolveComponent$4("v-chip");
  const _component_v_select = _resolveComponent$4("v-select");
  const _component_v_radio = _resolveComponent$4("v-radio");
  const _component_v_radio_group = _resolveComponent$4("v-radio-group");
  const _component_v_list_item_title = _resolveComponent$4("v-list-item-title");
  const _component_v_list_item_subtitle = _resolveComponent$4("v-list-item-subtitle");
  const _component_v_list_item = _resolveComponent$4("v-list-item");
  const _component_v_list = _resolveComponent$4("v-list");
  const _component_v_card_actions = _resolveComponent$4("v-card-actions");
  const _component_v_dialog = _resolveComponent$4("v-dialog");
  const _component_v_container = _resolveComponent$4("v-container");

  return (_openBlock$4(), _createBlock$4(_component_v_container, {
    fluid: "",
    class: "pa-4"
  }, {
    default: _withCtx$4(() => [
      _createVNode$4(_component_v_card, {
        flat: "",
        class: "rounded border status-card"
      }, {
        default: _withCtx$4(() => [
          _createVNode$4(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
            default: _withCtx$4(() => [
              _createVNode$4(_component_v_icon, {
                icon: "mdi-folder",
                class: "mr-2",
                color: "primary",
                size: "small"
              }),
              _cache[15] || (_cache[15] = _createElementVNode$4("span", null, "目录浏览", -1)),
              _createVNode$4(_component_v_spacer),
              _createVNode$4(_component_v_btn, {
                color: "primary",
                size: "small",
                variant: "text",
                "prepend-icon": "mdi-refresh",
                loading: loading.value,
                onClick: refreshCurrentDir
              }, {
                default: _withCtx$4(() => [...(_cache[14] || (_cache[14] = [
                  _createTextVNode$4("刷新", -1)
                ]))]),
                _: 1
              }, 8, ["loading"])
            ]),
            _: 1
          }),
          _createVNode$4(_component_v_card_text, { class: "px-3 py-2" }, {
            default: _withCtx$4(() => [
              (error.value)
                ? (_openBlock$4(), _createBlock$4(_component_v_alert, {
                    key: 0,
                    type: "error",
                    density: "compact",
                    class: "mb-2 text-caption",
                    variant: "tonal",
                    closable: "",
                    "onClick:close": _cache[0] || (_cache[0] = $event => (error.value = null))
                  }, {
                    default: _withCtx$4(() => [
                      _createTextVNode$4(_toDisplayString$3(error.value), 1)
                    ]),
                    _: 1
                  }))
                : _createCommentVNode$4("", true),
              (successMessage.value)
                ? (_openBlock$4(), _createBlock$4(_component_v_alert, {
                    key: 1,
                    type: "success",
                    density: "compact",
                    class: "mb-2 text-caption",
                    variant: "tonal",
                    closable: "",
                    "onClick:close": _cache[1] || (_cache[1] = $event => (successMessage.value = null))
                  }, {
                    default: _withCtx$4(() => [
                      _createTextVNode$4(_toDisplayString$3(successMessage.value), 1)
                    ]),
                    _: 1
                  }))
                : _createCommentVNode$4("", true),
              _createVNode$4(_component_v_row, { class: "mb-2" }, {
                default: _withCtx$4(() => [
                  _createVNode$4(_component_v_col, { cols: "12" }, {
                    default: _withCtx$4(() => [
                      _createVNode$4(_component_v_text_field, {
                        modelValue: searchKeyword.value,
                        "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((searchKeyword).value = $event)),
                        density: "compact",
                        variant: "outlined",
                        "hide-details": "",
                        placeholder: "搜索文件/目录",
                        "prepend-inner-icon": "mdi-magnify",
                        class: "search-field"
                      }, null, 8, ["modelValue"])
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              }),
              _createVNode$4(_component_v_row, { class: "mb-3" }, {
                default: _withCtx$4(() => [
                  _createVNode$4(_component_v_col, {
                    cols: "12",
                    sm: "4",
                    md: "2"
                  }, {
                    default: _withCtx$4(() => [
                      _createVNode$4(_component_v_btn, {
                        color: "primary",
                        size: "small",
                        variant: "tonal",
                        "prepend-icon": "mdi-download-multiple",
                        loading: batchStarting.value,
                        disabled: scrapingStatus.running,
                        onClick: scrapeCurrentDirectory,
                        class: "w-full"
                      }, {
                        default: _withCtx$4(() => [...(_cache[16] || (_cache[16] = [
                          _createTextVNode$4(" 刮削本目录 ", -1)
                        ]))]),
                        _: 1
                      }, 8, ["loading", "disabled"])
                    ]),
                    _: 1
                  }),
                  _createVNode$4(_component_v_col, {
                    cols: "12",
                    sm: "4",
                    md: "2"
                  }, {
                    default: _withCtx$4(() => [
                      _createVNode$4(_component_v_btn, {
                        color: "info",
                        size: "small",
                        variant: "tonal",
                        "prepend-icon": "mdi-bar-chart",
                        loading: scanningStats.value,
                        onClick: scanDirectoryStats,
                        class: "w-full"
                      }, {
                        default: _withCtx$4(() => [...(_cache[17] || (_cache[17] = [
                          _createTextVNode$4(" 扫描统计 ", -1)
                        ]))]),
                        _: 1
                      }, 8, ["loading"])
                    ]),
                    _: 1
                  }),
                  _createVNode$4(_component_v_col, {
                    cols: "12",
                    sm: "4",
                    md: "2"
                  }, {
                    default: _withCtx$4(() => [
                      _createVNode$4(_component_v_btn, {
                        color: "warning",
                        size: "small",
                        variant: "tonal",
                        "prepend-icon": "mdi-trash-can",
                        loading: batchStarting.value,
                        disabled: scrapingStatus.running,
                        onClick: cleanCurrentDirectorySubtitles,
                        class: "w-full"
                      }, {
                        default: _withCtx$4(() => [...(_cache[18] || (_cache[18] = [
                          _createTextVNode$4(" 清理字幕 ", -1)
                        ]))]),
                        _: 1
                      }, 8, ["loading", "disabled"])
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              }),
              _createVNode$4(_component_v_row, null, {
                default: _withCtx$4(() => [
                  _createVNode$4(_component_v_col, { cols: "12" }, {
                    default: _withCtx$4(() => [
                      (directoryContent.value)
                        ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_1$4, [
                            (loading.value)
                              ? (_openBlock$4(), _createBlock$4(_component_v_progress_linear, {
                                  key: 0,
                                  indeterminate: "",
                                  color: "primary",
                                  class: "mb-2"
                                }))
                              : _createCommentVNode$4("", true),
                            (scrapingStatus.running)
                              ? (_openBlock$4(), _createBlock$4(_component_v_card, {
                                  key: 1,
                                  class: "mb-4 bg-primary-lighten-5"
                                }, {
                                  default: _withCtx$4(() => [
                                    _createVNode$4(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2" }, {
                                      default: _withCtx$4(() => [
                                        _createVNode$4(_component_v_icon, {
                                          icon: "mdi-loader",
                                          color: "primary",
                                          size: "small",
                                          class: "mr-2 animate-spin"
                                        }),
                                        _cache[20] || (_cache[20] = _createTextVNode$4(" 正在刮削中 ", -1)),
                                        _createVNode$4(_component_v_spacer),
                                        _createVNode$4(_component_v_btn, {
                                          color: "error",
                                          size: "small",
                                          variant: "tonal",
                                          "prepend-icon": "mdi-stop",
                                          onClick: abortScraping
                                        }, {
                                          default: _withCtx$4(() => [...(_cache[19] || (_cache[19] = [
                                            _createTextVNode$4(" 中止 ", -1)
                                          ]))]),
                                          _: 1
                                        })
                                      ]),
                                      _: 1
                                    }),
                                    _createVNode$4(_component_v_card_text, { class: "px-3 py-2" }, {
                                      default: _withCtx$4(() => [
                                        _createVNode$4(_component_v_progress_linear, {
                                          value: scrapingStatus.total > 0 ? (scrapingStatus.processed / scrapingStatus.total * 100) : 0,
                                          color: "primary",
                                          height: "8",
                                          class: "mb-2"
                                        }, null, 8, ["value"]),
                                        _createElementVNode$4("div", _hoisted_2$3, [
                                          _createElementVNode$4("span", _hoisted_3$3, "当前文件: " + _toDisplayString$3(scrapingStatus.current_file || '-'), 1),
                                          _createElementVNode$4("span", _hoisted_4$3, _toDisplayString$3(scrapingStatus.processed) + " / " + _toDisplayString$3(scrapingStatus.total), 1)
                                        ]),
                                        _createElementVNode$4("div", _hoisted_5$2, [
                                          _createElementVNode$4("span", _hoisted_6$2, [
                                            _cache[21] || (_cache[21] = _createTextVNode$4("成功: ", -1)),
                                            _createElementVNode$4("span", _hoisted_7$1, _toDisplayString$3(scrapingStatus.success), 1),
                                            _cache[22] || (_cache[22] = _createTextVNode$4(" | 失败: ", -1)),
                                            _createElementVNode$4("span", _hoisted_8$1, _toDisplayString$3(scrapingStatus.failed), 1)
                                          ]),
                                          _createElementVNode$4("span", _hoisted_9$1, "耗时: " + _toDisplayString$3(formatDuration(scrapingStatus.duration)), 1)
                                        ])
                                      ]),
                                      _: 1
                                    })
                                  ]),
                                  _: 1
                                }))
                              : _createCommentVNode$4("", true),
                            (currentPath.value)
                              ? (_openBlock$4(), _createElementBlock$4("div", {
                                  key: 2,
                                  class: "back-item d-flex align-center py-2 mb-2",
                                  onClick: _cache[3] || (_cache[3] = $event => (goBack()))
                                }, [
                                  _createVNode$4(_component_v_icon, {
                                    icon: "mdi-keyboard-backspace",
                                    size: "small",
                                    color: "primary",
                                    class: "mr-2"
                                  }),
                                  _createElementVNode$4("span", _hoisted_10$1, _toDisplayString$3(directoryContent.value.is_root ? '返回目录列表' : '返回上级目录'), 1)
                                ]))
                              : _createCommentVNode$4("", true),
                            (_openBlock$4(true), _createElementBlock$4(_Fragment, null, _renderList(filteredItems.value, (item, index) => {
                              return (_openBlock$4(), _createElementBlock$4(_Fragment, { key: index }, [
                                (item.type === 'directory')
                                  ? (_openBlock$4(), _createElementBlock$4("div", {
                                      key: 0,
                                      class: "directory-item d-flex align-center py-2",
                                      onClick: $event => (navigateToPath(item.path))
                                    }, [
                                      _createVNode$4(_component_v_icon, {
                                        icon: "mdi-folder",
                                        size: "small",
                                        color: "primary",
                                        class: "mr-2"
                                      }),
                                      _createElementVNode$4("div", _hoisted_12, [
                                        _createElementVNode$4("span", _hoisted_13, _toDisplayString$3(item.name), 1),
                                        (item.manual_match)
                                          ? (_openBlock$4(), _createBlock$4(_component_v_chip, {
                                              key: 0,
                                              size: "small",
                                              color: "secondary",
                                              class: "ml-2",
                                              closable: "",
                                              onClick: _cache[4] || (_cache[4] = _withModifiers(() => {}, ["stop"])),
                                              "onClick:close": _withModifiers($event => (clearManualMatch(item, item.manual_scope)), ["stop"])
                                            }, {
                                              default: _withCtx$4(() => [
                                                _createTextVNode$4(_toDisplayString$3(manualChipText(item)), 1)
                                              ]),
                                              _: 2
                                            }, 1032, ["onClick:close"]))
                                          : _createCommentVNode$4("", true)
                                      ]),
                                      (item.scrape_status)
                                        ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_14, [
                                            _createElementVNode$4("span", {
                                              class: _normalizeClass(["text-caption", getScrapeStatusClass(item.scrape_status)])
                                            }, _toDisplayString$3(item.scrape_status.scraped_files) + "/" + _toDisplayString$3(item.scrape_status.total_files), 3)
                                          ]))
                                        : _createCommentVNode$4("", true),
                                      _createVNode$4(_component_v_btn, {
                                        icon: "mdi-download-multiple",
                                        size: "small",
                                        variant: "text",
                                        color: "primary",
                                        class: "mr-1",
                                        disabled: scrapingStatus.running,
                                        onClick: _withModifiers($event => (scrapeDirectory(item.path, true)), ["stop"])
                                      }, null, 8, ["disabled", "onClick"]),
                                      _createVNode$4(_component_v_btn, {
                                        icon: "mdi-magnify",
                                        size: "small",
                                        variant: "text",
                                        color: "secondary",
                                        class: "mr-1",
                                        onClick: _withModifiers($event => (openManualMatch(item)), ["stop"])
                                      }, null, 8, ["onClick"]),
                                      _createVNode$4(_component_v_icon, {
                                        icon: "mdi-chevron-right",
                                        size: "small",
                                        color: "grey"
                                      })
                                    ], 8, _hoisted_11))
                                  : (item.type === 'media')
                                    ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_15, [
                                        _createVNode$4(_component_v_icon, {
                                          icon: "mdi-video",
                                          size: "small",
                                          color: "info",
                                          class: "mr-2"
                                        }),
                                        _createElementVNode$4("div", _hoisted_16, [
                                          _createElementVNode$4("div", _hoisted_17, [
                                            _createElementVNode$4("span", _hoisted_18, _toDisplayString$3(item.name), 1),
                                            (item.danmu_count > 0)
                                              ? (_openBlock$4(), _createBlock$4(_component_v_chip, {
                                                  key: 0,
                                                  size: "small",
                                                  color: "info",
                                                  class: "ml-2"
                                                }, {
                                                  default: _withCtx$4(() => [
                                                    _createTextVNode$4(" 弹幕: " + _toDisplayString$3(item.danmu_count), 1)
                                                  ]),
                                                  _: 2
                                                }, 1024))
                                              : (_openBlock$4(), _createBlock$4(_component_v_chip, {
                                                  key: 1,
                                                  size: "small",
                                                  color: "grey",
                                                  class: "ml-2"
                                                }, {
                                                  default: _withCtx$4(() => [...(_cache[23] || (_cache[23] = [
                                                    _createTextVNode$4(" 无弹幕 ", -1)
                                                  ]))]),
                                                  _: 1
                                                })),
                                            (item.manual_match)
                                              ? (_openBlock$4(), _createBlock$4(_component_v_chip, {
                                                  key: 2,
                                                  size: "small",
                                                  color: "secondary",
                                                  class: "ml-2",
                                                  closable: "",
                                                  "onClick:close": _withModifiers($event => (clearManualMatch(item, item.manual_scope)), ["stop"])
                                                }, {
                                                  default: _withCtx$4(() => [
                                                    _createTextVNode$4(_toDisplayString$3(manualChipText(item)), 1)
                                                  ]),
                                                  _: 2
                                                }, 1032, ["onClick:close"]))
                                              : _createCommentVNode$4("", true)
                                          ])
                                        ]),
                                        _createVNode$4(_component_v_btn, {
                                          color: "secondary",
                                          size: "small",
                                          variant: "text",
                                          class: "mr-1",
                                          onClick: $event => (openManualMatch(item))
                                        }, {
                                          default: _withCtx$4(() => [
                                            _createVNode$4(_component_v_icon, {
                                              icon: "mdi-magnify",
                                              size: "small",
                                              class: "mr-1"
                                            }),
                                            _cache[24] || (_cache[24] = _createTextVNode$4(" 手动匹配 ", -1))
                                          ]),
                                          _: 1
                                        }, 8, ["onClick"]),
                                        _createVNode$4(_component_v_btn, {
                                          color: "primary",
                                          size: "small",
                                          variant: "text",
                                          loading: item.generating,
                                          onClick: $event => (generateDanmu(item))
                                        }, {
                                          default: _withCtx$4(() => [
                                            _createVNode$4(_component_v_icon, {
                                              icon: "mdi-download",
                                              size: "small",
                                              class: "mr-1"
                                            }),
                                            _cache[25] || (_cache[25] = _createTextVNode$4(" 刮削 ", -1))
                                          ]),
                                          _: 1
                                        }, 8, ["loading", "onClick"])
                                      ]))
                                    : _createCommentVNode$4("", true)
                              ], 64))
                            }), 128)),
                            (directoryContent.value.children && directoryContent.value.children.length === 0)
                              ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_19, [
                                  _createVNode$4(_component_v_alert, {
                                    type: "info",
                                    density: "compact",
                                    class: "mb-2 text-caption",
                                    variant: "tonal"
                                  }, {
                                    default: _withCtx$4(() => [...(_cache[26] || (_cache[26] = [
                                      _createTextVNode$4(" 该目录为空或没有支持的媒体文件 ", -1)
                                    ]))]),
                                    _: 1
                                  })
                                ]))
                              : _createCommentVNode$4("", true)
                          ]))
                        : (loading.value)
                          ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_20, [
                              _createVNode$4(_component_v_progress_linear, {
                                indeterminate: "",
                                color: "primary",
                                class: "mb-2"
                              }),
                              _cache[27] || (_cache[27] = _createElementVNode$4("div", { class: "text-caption text-grey" }, "正在扫描目录，请稍候...", -1))
                            ]))
                          : (notConfigured.value)
                            ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_21, [
                                _createVNode$4(_component_v_alert, {
                                  type: "info",
                                  density: "compact",
                                  class: "mb-2 text-caption",
                                  variant: "tonal"
                                }, {
                                  default: _withCtx$4(() => [...(_cache[28] || (_cache[28] = [
                                    _createTextVNode$4(" 请先在配置中设置刮削路径 ", -1)
                                  ]))]),
                                  _: 1
                                })
                              ]))
                            : (error.value)
                              ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_22, [
                                  _createVNode$4(_component_v_alert, {
                                    type: "error",
                                    density: "compact",
                                    class: "mb-2 text-caption",
                                    variant: "tonal"
                                  }, {
                                    default: _withCtx$4(() => [
                                      _createTextVNode$4(_toDisplayString$3(error.value), 1)
                                    ]),
                                    _: 1
                                  })
                                ]))
                              : (_openBlock$4(), _createElementBlock$4("div", _hoisted_23, [
                                  _createVNode$4(_component_v_alert, {
                                    type: "info",
                                    density: "compact",
                                    class: "mb-2 text-caption",
                                    variant: "tonal"
                                  }, {
                                    default: _withCtx$4(() => [...(_cache[29] || (_cache[29] = [
                                      _createTextVNode$4(" 请先在配置中设置刮削路径 ", -1)
                                    ]))]),
                                    _: 1
                                  })
                                ]))
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode$4(_component_v_dialog, {
        modelValue: manualDialog.value,
        "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((manualDialog).value = $event)),
        "max-width": "720"
      }, {
        default: _withCtx$4(() => [
          _createVNode$4(_component_v_card, null, {
            default: _withCtx$4(() => [
              _createVNode$4(_component_v_card_title, { class: "text-subtitle-1" }, {
                default: _withCtx$4(() => [...(_cache[30] || (_cache[30] = [
                  _createTextVNode$4(" 手动匹配弹幕 ", -1)
                ]))]),
                _: 1
              }),
              _createVNode$4(_component_v_card_text, null, {
                default: _withCtx$4(() => [
                  _createElementVNode$4("div", _hoisted_24, " 当前选择：" + _toDisplayString$3(manualTargetItem.value?.name || '未选择文件'), 1),
                  (manualExistingMatch.value)
                    ? (_openBlock$4(), _createBlock$4(_component_v_alert, {
                        key: 0,
                        type: "info",
                        density: "compact",
                        variant: "tonal",
                        class: "mb-2 text-caption"
                      }, {
                        default: _withCtx$4(() => [
                          _createTextVNode$4(" 已匹配（" + _toDisplayString$3(scopeLabel(manualExistingScope.value)) + "）：" + _toDisplayString$3(manualExistingMatch.value.animeTitle || `ID ${manualExistingMatch.value.animeId}`) + " ", 1),
                          (manualExistingOffset.value)
                            ? (_openBlock$4(), _createElementBlock$4("span", _hoisted_25, "（集数偏移 " + _toDisplayString$3(formatOffset(manualExistingOffset.value)) + "）", 1))
                            : _createCommentVNode$4("", true)
                        ]),
                        _: 1
                      }))
                    : _createCommentVNode$4("", true),
                  (manualSearchError.value)
                    ? (_openBlock$4(), _createBlock$4(_component_v_alert, {
                        key: 1,
                        type: "error",
                        density: "compact",
                        variant: "tonal",
                        class: "mb-2 text-caption",
                        closable: "",
                        "onClick:close": _cache[5] || (_cache[5] = $event => (manualSearchError.value = null))
                      }, {
                        default: _withCtx$4(() => [
                          _createTextVNode$4(_toDisplayString$3(manualSearchError.value), 1)
                        ]),
                        _: 1
                      }))
                    : _createCommentVNode$4("", true),
                  _createVNode$4(_component_v_row, null, {
                    default: _withCtx$4(() => [
                      _createVNode$4(_component_v_col, {
                        cols: "12",
                        md: "6"
                      }, {
                        default: _withCtx$4(() => [
                          _createVNode$4(_component_v_text_field, {
                            modelValue: manualSearchKeyword.value,
                            "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((manualSearchKeyword).value = $event)),
                            label: "搜索关键字",
                            density: "compact",
                            variant: "outlined",
                            clearable: "",
                            "hide-details": "",
                            onKeyup: _withKeys(performManualSearch, ["enter"])
                          }, null, 8, ["modelValue"])
                        ]),
                        _: 1
                      }),
                      _createVNode$4(_component_v_col, {
                        cols: "12",
                        md: "4"
                      }, {
                        default: _withCtx$4(() => [
                          _createVNode$4(_component_v_select, {
                            modelValue: manualSearchType.value,
                            "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((manualSearchType).value = $event)),
                            items: manualTypeOptions,
                            "item-title": "title",
                            "item-value": "value",
                            density: "compact",
                            variant: "outlined",
                            "hide-details": "",
                            label: "类型"
                          }, null, 8, ["modelValue"])
                        ]),
                        _: 1
                      }),
                      _createVNode$4(_component_v_col, {
                        cols: "12",
                        md: "2",
                        class: "d-flex align-center"
                      }, {
                        default: _withCtx$4(() => [
                          _createVNode$4(_component_v_btn, {
                            color: "primary",
                            block: "",
                            loading: manualSearchLoading.value,
                            onClick: performManualSearch
                          }, {
                            default: _withCtx$4(() => [...(_cache[31] || (_cache[31] = [
                              _createTextVNode$4(" 搜索 ", -1)
                            ]))]),
                            _: 1
                          }, 8, ["loading"])
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  }),
                  (manualSearchLoading.value)
                    ? (_openBlock$4(), _createBlock$4(_component_v_progress_linear, {
                        key: 2,
                        indeterminate: "",
                        color: "primary",
                        class: "mb-2"
                      }))
                    : _createCommentVNode$4("", true),
                  (manualTargetItem.value && manualTargetItem.value.type === 'media')
                    ? (_openBlock$4(), _createBlock$4(_component_v_row, { key: 3 }, {
                        default: _withCtx$4(() => [
                          _createVNode$4(_component_v_col, { cols: "12" }, {
                            default: _withCtx$4(() => [
                              _createVNode$4(_component_v_radio_group, {
                                modelValue: manualScope.value,
                                "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((manualScope).value = $event)),
                                inline: "",
                                density: "compact",
                                "hide-details": ""
                              }, {
                                default: _withCtx$4(() => [
                                  _createVNode$4(_component_v_radio, {
                                    label: "仅当前文件",
                                    value: "file"
                                  }),
                                  _createVNode$4(_component_v_radio, {
                                    label: "整目录",
                                    value: "directory"
                                  })
                                ]),
                                _: 1
                              }, 8, ["modelValue"])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }))
                    : _createCommentVNode$4("", true),
                  _createVNode$4(_component_v_row, null, {
                    default: _withCtx$4(() => [
                      _createVNode$4(_component_v_col, {
                        cols: "12",
                        md: "5"
                      }, {
                        default: _withCtx$4(() => [
                          _createVNode$4(_component_v_text_field, {
                            modelValue: manualEpisodeOffset.value,
                            "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((manualEpisodeOffset).value = $event)),
                            label: "集数偏移",
                            type: "number",
                            density: "compact",
                            variant: "outlined",
                            hint: "本地集数 + 偏移 = 弹弹集数，如本地 13 对应弹弹 1 则填 -12",
                            "persistent-hint": ""
                          }, null, 8, ["modelValue"])
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  }),
                  (!manualSearchLoading.value && manualSearchPerformed.value && manualSearchResults.value.length === 0)
                    ? (_openBlock$4(), _createBlock$4(_component_v_alert, {
                        key: 4,
                        type: "info",
                        density: "compact",
                        variant: "tonal",
                        class: "mb-2 text-caption"
                      }, {
                        default: _withCtx$4(() => [...(_cache[32] || (_cache[32] = [
                          _createTextVNode$4(" 未找到匹配结果，请调整关键字后再试。 ", -1)
                        ]))]),
                        _: 1
                      }))
                    : _createCommentVNode$4("", true),
                  (manualSearchResults.value.length > 0)
                    ? (_openBlock$4(), _createBlock$4(_component_v_list, {
                        key: 5,
                        lines: "two",
                        density: "comfortable"
                      }, {
                        default: _withCtx$4(() => [
                          (_openBlock$4(true), _createElementBlock$4(_Fragment, null, _renderList(manualSearchResults.value, (anime) => {
                            return (_openBlock$4(), _createBlock$4(_component_v_list_item, {
                              key: anime.animeId,
                              active: manualSelected.value && manualSelected.value.animeId === anime.animeId,
                              onClick: $event => (selectManualResult(anime))
                            }, {
                              append: _withCtx$4(() => [
                                _createVNode$4(_component_v_btn, {
                                  icon: "mdi-check",
                                  size: "small",
                                  variant: "text",
                                  color: manualSelected.value && manualSelected.value.animeId === anime.animeId ? 'primary' : 'grey'
                                }, null, 8, ["color"])
                              ]),
                              default: _withCtx$4(() => [
                                _createVNode$4(_component_v_list_item_title, null, {
                                  default: _withCtx$4(() => [
                                    _createTextVNode$4(_toDisplayString$3(anime.animeTitle), 1)
                                  ]),
                                  _: 2
                                }, 1024),
                                _createVNode$4(_component_v_list_item_subtitle, null, {
                                  default: _withCtx$4(() => [
                                    _createTextVNode$4(_toDisplayString$3(anime.typeDescription || '未知类型') + " ", 1),
                                    (anime.episodeCount)
                                      ? (_openBlock$4(), _createElementBlock$4("span", _hoisted_26, " · " + _toDisplayString$3(anime.episodeCount) + " 集", 1))
                                      : _createCommentVNode$4("", true),
                                    (anime.rating)
                                      ? (_openBlock$4(), _createElementBlock$4("span", _hoisted_27, " · 评分 " + _toDisplayString$3(anime.rating), 1))
                                      : _createCommentVNode$4("", true),
                                    (anime.startDate)
                                      ? (_openBlock$4(), _createElementBlock$4("span", _hoisted_28, " · " + _toDisplayString$3(formatDate(anime.startDate)), 1))
                                      : _createCommentVNode$4("", true)
                                  ]),
                                  _: 2
                                }, 1024)
                              ]),
                              _: 2
                            }, 1032, ["active", "onClick"]))
                          }), 128))
                        ]),
                        _: 1
                      }))
                    : _createCommentVNode$4("", true)
                ]),
                _: 1
              }),
              _createVNode$4(_component_v_card_actions, null, {
                default: _withCtx$4(() => [
                  (manualExistingMatch.value)
                    ? (_openBlock$4(), _createBlock$4(_component_v_btn, {
                        key: 0,
                        color: "grey",
                        variant: "text",
                        onClick: _cache[10] || (_cache[10] = $event => (clearManualMatch(manualTargetItem.value, manualExistingScope.value || (manualTargetItem.value?.type === 'directory' ? 'directory' : 'file'), true)))
                      }, {
                        default: _withCtx$4(() => [...(_cache[33] || (_cache[33] = [
                          _createTextVNode$4(" 清除匹配 ", -1)
                        ]))]),
                        _: 1
                      }))
                    : _createCommentVNode$4("", true),
                  _createVNode$4(_component_v_spacer),
                  _createVNode$4(_component_v_btn, {
                    variant: "text",
                    onClick: closeManualDialog
                  }, {
                    default: _withCtx$4(() => [...(_cache[34] || (_cache[34] = [
                      _createTextVNode$4("取消", -1)
                    ]))]),
                    _: 1
                  }),
                  _createVNode$4(_component_v_btn, {
                    color: "primary",
                    disabled: !manualSelected.value,
                    loading: manualSaving.value,
                    onClick: confirmManualMatch
                  }, {
                    default: _withCtx$4(() => [...(_cache[35] || (_cache[35] = [
                      _createTextVNode$4(" 保存 ", -1)
                    ]))]),
                    _: 1
                  }, 8, ["disabled", "loading"])
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }, 8, ["modelValue"]),
      _createVNode$4(_component_v_dialog, {
        modelValue: cleanConfirmDialog.value,
        "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => ((cleanConfirmDialog).value = $event)),
        "max-width": "500"
      }, {
        default: _withCtx$4(() => [
          _createVNode$4(_component_v_card, null, {
            default: _withCtx$4(() => [
              _createVNode$4(_component_v_card_title, { class: "text-subtitle-1" }, {
                default: _withCtx$4(() => [
                  _createVNode$4(_component_v_icon, {
                    icon: "mdi-alert-circle",
                    color: "warning",
                    class: "mr-2"
                  }),
                  _cache[36] || (_cache[36] = _createTextVNode$4(" 确认清理字幕 ", -1))
                ]),
                _: 1
              }),
              _createVNode$4(_component_v_card_text, null, {
                default: _withCtx$4(() => [
                  _cache[38] || (_cache[38] = _createElementVNode$4("div", { class: "text-body-1" }, " 确定要清理当前目录下的所有弹幕和合并字幕文件吗？ ", -1)),
                  _createElementVNode$4("div", _hoisted_29, " 目录：" + _toDisplayString$3(currentPath.value), 1),
                  _createVNode$4(_component_v_alert, {
                    type: "warning",
                    density: "compact",
                    variant: "tonal",
                    class: "mt-3 text-caption"
                  }, {
                    default: _withCtx$4(() => [...(_cache[37] || (_cache[37] = [
                      _createTextVNode$4(" 此操作不可恢复，清理后需重新刮削获取弹幕。 ", -1)
                    ]))]),
                    _: 1
                  })
                ]),
                _: 1
              }),
              _createVNode$4(_component_v_card_actions, { class: "px-6 py-3" }, {
                default: _withCtx$4(() => [
                  _createVNode$4(_component_v_spacer),
                  _createVNode$4(_component_v_btn, {
                    color: "grey",
                    variant: "outlined",
                    size: "small",
                    class: "mr-3",
                    onClick: _cache[12] || (_cache[12] = $event => (cleanConfirmDialog.value = false))
                  }, {
                    default: _withCtx$4(() => [...(_cache[39] || (_cache[39] = [
                      _createTextVNode$4("取消", -1)
                    ]))]),
                    _: 1
                  }),
                  _createVNode$4(_component_v_btn, {
                    color: "warning",
                    variant: "tonal",
                    size: "small",
                    onClick: confirmCleanSubtitles
                  }, {
                    default: _withCtx$4(() => [...(_cache[40] || (_cache[40] = [
                      _createTextVNode$4("确认清理", -1)
                    ]))]),
                    _: 1
                  }),
                  _createVNode$4(_component_v_spacer)
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }, 8, ["modelValue"])
    ]),
    _: 1
  }))
}
}

};
const BrowseView = /*#__PURE__*/_export_sfc(_sfc_main$4, [['__scopeId',"data-v-fbde3429"]]);

const {resolveComponent:_resolveComponent$3,createVNode:_createVNode$3,toDisplayString:_toDisplayString$2,createElementVNode:_createElementVNode$3,createTextVNode:_createTextVNode$3,withCtx:_withCtx$3,openBlock:_openBlock$3,createBlock:_createBlock$3,createCommentVNode:_createCommentVNode$3,mergeProps:_mergeProps,createElementBlock:_createElementBlock$3} = await importShared('vue');


const _hoisted_1$3 = { class: "text-sm text-grey ml-2" };
const _hoisted_2$2 = {
  class: "d-flex align-center",
  style: {"gap":"8px"}
};
const _hoisted_3$2 = ["title"];
const _hoisted_4$2 = {
  key: 1,
  class: "text-center py-8 text-grey"
};

const {ref: ref$3,reactive,onMounted: onMounted$2} = await importShared('vue');



const _sfc_main$3 = {
  __name: 'RetryTasks',
  props: {
  api: {
    type: [Object, Function],
    required: true,
  }
},
  setup(__props) {

const props = __props;

const tasks = ref$3([]);
const total = ref$3(0);
const minDanmuCount = ref$3(null);
const maxRetryTimes = ref$3(null);
const loading = ref$3(false);
const actionLoading = reactive({});
const message = reactive({ text: '', type: 'success' });

function showMsg(text, type = 'success') {
  message.text = text;
  message.type = type;
  setTimeout(() => { message.text = ''; }, 4000);
}

const headers = [
  { title: '文件路径', value: 'file_path', width: '30%' },
  { title: '重试次数', value: 'retry_count', width: '10%' },
  { title: '上次尝试', value: 'last_attempt', width: '15%' },
  { title: '下次重试', value: 'next_retry_time', width: '15%' },
  { title: '错误类型', value: 'error_type', width: '10%' },
  { title: '弹幕数量', value: 'last_danmu_count', width: '10%' },
  { title: '操作', value: 'actions', width: '10%' }
];

const fetchTasks = async () => {
  loading.value = true;
  try {
    const data = await props.api.get('plugin/DanmuTV/retry_tasks');
    if (data && data.success) {
      tasks.value = Object.values(data.data.tasks || {});
      total.value = data.data.total || 0;
      minDanmuCount.value = data.data.min_danmu_count || 100;
      maxRetryTimes.value = data.data.max_retry_times || 10;
    }
  } catch (error) {
    console.error('获取重试任务失败:', error);
  } finally {
    loading.value = false;
  }
};

const processAll = async () => {
  actionLoading.processAll = true;
  try {
    const res = await props.api.get('plugin/DanmuTV/process_retry_tasks');
    if (res && res.success) {
      showMsg('全部重试已执行完成');
    } else {
      showMsg(res?.message || '全部重试失败', 'error');
    }
    await fetchTasks();
  } catch (error) {
    console.error('处理重试任务失败:', error);
    showMsg('全部重试失败: ' + (error.message || ''), 'error');
  } finally {
    actionLoading.processAll = false;
  }
};

const clearAll = async () => {
  actionLoading.clearAll = true;
  try {
    const res = await props.api.get('plugin/DanmuTV/clear_retry_tasks');
    if (res && res.success) {
      showMsg('已清空全部重试任务');
    } else {
      showMsg(res?.message || '清空失败', 'error');
    }
    await fetchTasks();
  } catch (error) {
    console.error('清空重试任务失败:', error);
    showMsg('清空失败: ' + (error.message || ''), 'error');
  } finally {
    actionLoading.clearAll = false;
  }
};

const retrySingle = async (filePath) => {
  actionLoading[`retry_${filePath}`] = true;
  try {
    const res = await props.api.get('plugin/DanmuTV/generate_danmu', {
      params: { file_path: filePath }
    });
    if (res && res.success) {
      showMsg(`重试成功: ${getFileName(filePath)} (${res.data?.danmu_count || 0}条)`);
    } else {
      showMsg(res?.message || `重试失败: ${getFileName(filePath)}`, 'error');
    }
    await fetchTasks();
  } catch (error) {
    console.error('重试单个任务失败:', error);
    showMsg('重试失败: ' + (error.message || ''), 'error');
  } finally {
    actionLoading[`retry_${filePath}`] = false;
  }
};

const removeSingle = async (filePath) => {
  actionLoading[`remove_${filePath}`] = true;
  try {
    const res = await props.api.get('plugin/DanmuTV/remove_retry_task', {
      params: { file_path: filePath }
    });
    if (res && res.success) {
      showMsg(`已移除: ${getFileName(filePath)}`);
    } else {
      showMsg(res?.message || '移除失败', 'error');
    }
    await fetchTasks();
  } catch (error) {
    console.error('移除重试任务失败:', error);
    showMsg('移除失败: ' + (error.message || ''), 'error');
  } finally {
    actionLoading[`remove_${filePath}`] = false;
  }
};

const getFileName = (filePath) => {
  return filePath.split('/').pop().split('\\').pop() || filePath
};

const getErrorLabel = (errorType) => {
  const labels = {
    'rate_limit': '429限流',
    'no_data': '无弹幕',
    'no_match': '未匹配',
    'network': '网络错误',
    'unknown': '未知'
  };
  return labels[errorType] || errorType
};

const getErrorColor = (errorType) => {
  const colors = {
    'rate_limit': 'warning',
    'no_data': 'info',
    'no_match': 'secondary',
    'network': 'error',
    'unknown': 'grey'
  };
  return colors[errorType] || 'grey'
};

onMounted$2(() => {
  fetchTasks();
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$3("v-icon");
  const _component_v_spacer = _resolveComponent$3("v-spacer");
  const _component_v_chip = _resolveComponent$3("v-chip");
  const _component_v_btn = _resolveComponent$3("v-btn");
  const _component_v_card_title = _resolveComponent$3("v-card-title");
  const _component_v_alert = _resolveComponent$3("v-alert");
  const _component_v_tooltip = _resolveComponent$3("v-tooltip");
  const _component_v_data_table = _resolveComponent$3("v-data-table");
  const _component_v_card_text = _resolveComponent$3("v-card-text");
  const _component_v_card = _resolveComponent$3("v-card");
  const _component_v_container = _resolveComponent$3("v-container");

  return (_openBlock$3(), _createBlock$3(_component_v_container, {
    fluid: "",
    class: "pa-4"
  }, {
    default: _withCtx$3(() => [
      _createVNode$3(_component_v_card, {
        flat: "",
        class: "rounded border status-card"
      }, {
        default: _withCtx$3(() => [
          _createVNode$3(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5 flex-wrap" }, {
            default: _withCtx$3(() => [
              _createVNode$3(_component_v_icon, {
                icon: "mdi-alert-circle-outline",
                color: "warning",
                size: "small",
                class: "mr-2"
              }),
              _cache[3] || (_cache[3] = _createTextVNode$3(" 重试任务列表 ", -1)),
              _createElementVNode$3("span", _hoisted_1$3, "(" + _toDisplayString$2(total.value) + " 个)", 1),
              _createVNode$3(_component_v_spacer),
              _createElementVNode$3("div", _hoisted_2$2, [
                (minDanmuCount.value)
                  ? (_openBlock$3(), _createBlock$3(_component_v_chip, {
                      key: 0,
                      size: "small",
                      variant: "tonal",
                      color: "grey"
                    }, {
                      default: _withCtx$3(() => [
                        _createTextVNode$3("最小弹幕: " + _toDisplayString$2(minDanmuCount.value), 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode$3("", true),
                (maxRetryTimes.value)
                  ? (_openBlock$3(), _createBlock$3(_component_v_chip, {
                      key: 1,
                      size: "small",
                      variant: "tonal",
                      color: "grey"
                    }, {
                      default: _withCtx$3(() => [
                        _createTextVNode$3("最大重试: " + _toDisplayString$2(maxRetryTimes.value), 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode$3("", true),
                _createVNode$3(_component_v_btn, {
                  color: "primary",
                  size: "small",
                  variant: "tonal",
                  "prepend-icon": "mdi-refresh",
                  onClick: processAll,
                  loading: actionLoading.processAll
                }, {
                  default: _withCtx$3(() => [...(_cache[1] || (_cache[1] = [
                    _createTextVNode$3(" 全部重试 ", -1)
                  ]))]),
                  _: 1
                }, 8, ["loading"]),
                _createVNode$3(_component_v_btn, {
                  color: "error",
                  size: "small",
                  variant: "tonal",
                  "prepend-icon": "mdi-delete",
                  onClick: clearAll,
                  loading: actionLoading.clearAll
                }, {
                  default: _withCtx$3(() => [...(_cache[2] || (_cache[2] = [
                    _createTextVNode$3(" 清空全部 ", -1)
                  ]))]),
                  _: 1
                }, 8, ["loading"])
              ])
            ]),
            _: 1
          }),
          _createVNode$3(_component_v_card_text, { class: "px-3 py-2" }, {
            default: _withCtx$3(() => [
              (message.text)
                ? (_openBlock$3(), _createBlock$3(_component_v_alert, {
                    key: 0,
                    type: message.type,
                    density: "compact",
                    class: "mb-2 text-caption",
                    variant: "tonal",
                    closable: "",
                    "onClick:close": _cache[0] || (_cache[0] = $event => (message.text = ''))
                  }, {
                    default: _withCtx$3(() => [
                      _createTextVNode$3(_toDisplayString$2(message.text), 1)
                    ]),
                    _: 1
                  }, 8, ["type"]))
                : _createCommentVNode$3("", true),
              _createVNode$3(_component_v_data_table, {
                headers: headers,
                items: tasks.value,
                "items-per-page": 10,
                loading: loading.value,
                density: "compact",
                class: "elevation-1 retry-table"
              }, {
                "item.file_path": _withCtx$3(({ item }) => [
                  _createElementVNode$3("div", {
                    class: "text-truncate",
                    title: item.file_path
                  }, _toDisplayString$2(getFileName(item.file_path)), 9, _hoisted_3$2)
                ]),
                "item.error_type": _withCtx$3(({ item }) => [
                  _createVNode$3(_component_v_tooltip, {
                    text: item.error_message || getErrorLabel(item.error_type),
                    location: "top"
                  }, {
                    activator: _withCtx$3(({ props }) => [
                      _createVNode$3(_component_v_chip, _mergeProps({
                        color: getErrorColor(item.error_type),
                        size: "small"
                      }, props), {
                        default: _withCtx$3(() => [
                          _createTextVNode$3(_toDisplayString$2(getErrorLabel(item.error_type)), 1)
                        ]),
                        _: 2
                      }, 1040, ["color"])
                    ]),
                    _: 2
                  }, 1032, ["text"])
                ]),
                "item.actions": _withCtx$3(({ item }) => [
                  _createVNode$3(_component_v_btn, {
                    icon: "",
                    size: "small",
                    color: "primary",
                    onClick: $event => (retrySingle(item.file_path)),
                    loading: actionLoading[`retry_${item.file_path}`]
                  }, {
                    default: _withCtx$3(() => [
                      _createVNode$3(_component_v_icon, { icon: "mdi-refresh" })
                    ]),
                    _: 1
                  }, 8, ["onClick", "loading"]),
                  _createVNode$3(_component_v_btn, {
                    icon: "",
                    size: "small",
                    color: "error",
                    onClick: $event => (removeSingle(item.file_path)),
                    loading: actionLoading[`remove_${item.file_path}`]
                  }, {
                    default: _withCtx$3(() => [
                      _createVNode$3(_component_v_icon, { icon: "mdi-delete" })
                    ]),
                    _: 1
                  }, 8, ["onClick", "loading"])
                ]),
                _: 1
              }, 8, ["items", "loading"]),
              (total.value === 0)
                ? (_openBlock$3(), _createElementBlock$3("div", _hoisted_4$2, [
                    _createVNode$3(_component_v_icon, {
                      icon: "mdi-check-circle",
                      size: "48",
                      color: "success"
                    }),
                    _cache[4] || (_cache[4] = _createElementVNode$3("p", { class: "mt-2" }, "暂无重试任务", -1))
                  ]))
                : _createCommentVNode$3("", true)
            ]),
            _: 1
          })
        ]),
        _: 1
      })
    ]),
    _: 1
  }))
}
}

};
const RetryTasks = /*#__PURE__*/_export_sfc(_sfc_main$3, [['__scopeId',"data-v-485e1aa4"]]);

const {resolveComponent:_resolveComponent$2,createVNode:_createVNode$2,toDisplayString:_toDisplayString$1,createElementVNode:_createElementVNode$2,createTextVNode:_createTextVNode$2,withCtx:_withCtx$2,openBlock:_openBlock$2,createElementBlock:_createElementBlock$2,createCommentVNode:_createCommentVNode$2,createBlock:_createBlock$2} = await importShared('vue');


const _hoisted_1$2 = { class: "text-sm text-grey ml-2" };
const _hoisted_2$1 = ["title"];
const _hoisted_3$1 = { class: "text-success" };
const _hoisted_4$1 = { class: "text-error" };
const _hoisted_5$1 = { colspan: "7" };
const _hoisted_6$1 = { key: 0 };
const _hoisted_7 = {
  key: 0,
  class: "text-error text-caption"
};
const _hoisted_8 = {
  key: 1,
  class: "text-grey"
};
const _hoisted_9 = {
  key: 1,
  class: "text-grey text-sm"
};
const _hoisted_10 = {
  key: 0,
  class: "text-center py-8 text-grey"
};

const {ref: ref$2,onMounted: onMounted$1} = await importShared('vue');



const _sfc_main$2 = {
  __name: 'History',
  props: {
  api: { 
    type: [Object, Function],
    required: true,
  }
},
  setup(__props) {

const props = __props;

const history = ref$2([]);
const total = ref$2(0);
const loading = ref$2(false);

const headers = [
  { title: '时间', value: 'timestamp', width: '18%' },
  { title: '类型', value: 'type', width: '10%' },
  { title: '路径', value: 'path', width: '30%' },
  { title: '处理数', value: 'processed', width: '10%' },
  { title: '结果', value: 'result', width: '15%' },
  { title: '耗时', value: 'duration', width: '10%' }
];

const detailHeaders = [
  { title: '文件', value: 'file', width: '40%' },
  { title: '结果', value: 'result', width: '10%' },
  { title: '弹幕数', value: 'danmu_count', width: '10%' },
  { title: '错误信息', value: 'error', width: '40%' }
];

const fetchHistory = async () => {
  loading.value = true;
  try {
    const data = await props.api.get('plugin/DanmuTV/history', {
      params: { include_details: true }
    });
    if (data && data.success) {
      history.value = data.data.history || [];
      total.value = data.data.total || 0;
    }
  } catch (error) {
    console.error('获取历史记录失败:', error);
  } finally {
    loading.value = false;
  }
};

const clearHistory = async () => {
  try {
    await props.api.post('plugin/DanmuTV/clear_history');
    await fetchHistory();
  } catch (error) {
    console.error('清空历史记录失败:', error);
  }
};

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
};

const formatDuration = (seconds) => {
  if (!seconds) return '0秒'
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`
};

const getTypeLabel = (type) => {
  const labels = {
    'batch': '批量刮削',
    'single': '单文件刮削',
    'retry': '重试任务'
  };
  return labels[type] || type
};

const getTypeColor = (type) => {
  const colors = {
    'batch': 'primary',
    'single': 'info',
    'retry': 'warning'
  };
  return colors[type] || 'info'
};

onMounted$1(() => {
  fetchHistory();
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$2("v-icon");
  const _component_v_spacer = _resolveComponent$2("v-spacer");
  const _component_v_btn = _resolveComponent$2("v-btn");
  const _component_v_card_title = _resolveComponent$2("v-card-title");
  const _component_v_chip = _resolveComponent$2("v-chip");
  const _component_v_data_table = _resolveComponent$2("v-data-table");
  const _component_v_card_text = _resolveComponent$2("v-card-text");
  const _component_v_card = _resolveComponent$2("v-card");
  const _component_v_container = _resolveComponent$2("v-container");

  return (_openBlock$2(), _createBlock$2(_component_v_container, {
    fluid: "",
    class: "pa-4"
  }, {
    default: _withCtx$2(() => [
      _createVNode$2(_component_v_card, {
        flat: "",
        class: "rounded border status-card"
      }, {
        default: _withCtx$2(() => [
          _createVNode$2(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
            default: _withCtx$2(() => [
              _createVNode$2(_component_v_icon, {
                icon: "mdi-history",
                color: "primary",
                size: "small",
                class: "mr-2"
              }),
              _cache[1] || (_cache[1] = _createTextVNode$2(" 历史记录 ", -1)),
              _createElementVNode$2("span", _hoisted_1$2, "(" + _toDisplayString$1(total.value) + " 条)", 1),
              _createVNode$2(_component_v_spacer),
              _createVNode$2(_component_v_btn, {
                color: "error",
                size: "small",
                variant: "tonal",
                "prepend-icon": "mdi-delete",
                onClick: clearHistory
              }, {
                default: _withCtx$2(() => [...(_cache[0] || (_cache[0] = [
                  _createTextVNode$2(" 清空历史 ", -1)
                ]))]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createVNode$2(_component_v_card_text, { class: "px-3 py-2" }, {
            default: _withCtx$2(() => [
              _createVNode$2(_component_v_data_table, {
                headers: headers,
                items: history.value,
                "items-per-page": 10,
                loading: loading.value,
                density: "compact",
                class: "elevation-1 history-table",
                "item-key": "id",
                "show-expand": ""
              }, {
                "item.timestamp": _withCtx$2(({ item }) => [
                  _createTextVNode$2(_toDisplayString$1(formatTime(item.timestamp)), 1)
                ]),
                "item.type": _withCtx$2(({ item }) => [
                  _createVNode$2(_component_v_chip, {
                    color: getTypeColor(item.type),
                    size: "small"
                  }, {
                    default: _withCtx$2(() => [
                      _createTextVNode$2(_toDisplayString$1(getTypeLabel(item.type)), 1)
                    ]),
                    _: 2
                  }, 1032, ["color"])
                ]),
                "item.path": _withCtx$2(({ item }) => [
                  _createElementVNode$2("div", {
                    class: "text-truncate",
                    title: item.path
                  }, _toDisplayString$1(item.path), 9, _hoisted_2$1)
                ]),
                "item.result": _withCtx$2(({ item }) => [
                  _createElementVNode$2("span", _hoisted_3$1, "成功 " + _toDisplayString$1(item.success), 1),
                  _cache[2] || (_cache[2] = _createElementVNode$2("span", { class: "mx-2" }, "/", -1)),
                  _createElementVNode$2("span", _hoisted_4$1, "失败 " + _toDisplayString$1(item.failed), 1)
                ]),
                "item.duration": _withCtx$2(({ item }) => [
                  _createTextVNode$2(_toDisplayString$1(formatDuration(item.duration)), 1)
                ]),
                "expanded-item": _withCtx$2(({ item }) => [
                  _createElementVNode$2("td", _hoisted_5$1, [
                    (item.details && item.details.length > 0)
                      ? (_openBlock$2(), _createElementBlock$2("div", _hoisted_6$1, [
                          _createVNode$2(_component_v_data_table, {
                            headers: detailHeaders,
                            items: item.details,
                            "hide-default-footer": "",
                            density: "compact",
                            class: "elevation-0"
                          }, {
                            "item.result": _withCtx$2(({ item }) => [
                              _createVNode$2(_component_v_icon, {
                                icon: item.result === 'success' ? 'mdi-check-circle' : 'mdi-close-circle',
                                color: item.result === 'success' ? 'success' : 'error',
                                size: "small"
                              }, null, 8, ["icon", "color"])
                            ]),
                            "item.error": _withCtx$2(({ item }) => [
                              (item.error)
                                ? (_openBlock$2(), _createElementBlock$2("span", _hoisted_7, _toDisplayString$1(item.error), 1))
                                : (_openBlock$2(), _createElementBlock$2("span", _hoisted_8, "-"))
                            ]),
                            _: 2
                          }, 1032, ["items"])
                        ]))
                      : (_openBlock$2(), _createElementBlock$2("div", _hoisted_9, "暂无详情"))
                  ])
                ]),
                _: 1
              }, 8, ["items", "loading"]),
              (total.value === 0)
                ? (_openBlock$2(), _createElementBlock$2("div", _hoisted_10, [
                    _createVNode$2(_component_v_icon, {
                      icon: "mdi-history",
                      size: "48"
                    }),
                    _cache[3] || (_cache[3] = _createElementVNode$2("p", { class: "mt-2" }, "暂无历史记录", -1))
                  ]))
                : _createCommentVNode$2("", true)
            ]),
            _: 1
          })
        ]),
        _: 1
      })
    ]),
    _: 1
  }))
}
}

};
const History = /*#__PURE__*/_export_sfc(_sfc_main$2, [['__scopeId',"data-v-6f32b23e"]]);

const {resolveComponent:_resolveComponent$1,createVNode:_createVNode$1,createTextVNode:_createTextVNode$1,withCtx:_withCtx$1,openBlock:_openBlock$1,createElementBlock:_createElementBlock$1,createCommentVNode:_createCommentVNode$1,toDisplayString:_toDisplayString,createBlock:_createBlock$1,createElementVNode:_createElementVNode$1} = await importShared('vue');


const _hoisted_1$1 = {
  key: 0,
  class: "text-caption text-error"
};
const _hoisted_2 = {
  class: "d-flex align-center flex-wrap mb-4",
  style: {"gap":"8px"}
};
const _hoisted_3 = {
  key: 0,
  class: "text-center py-8"
};
const _hoisted_4 = ["title"];
const _hoisted_5 = {
  key: 2,
  class: "text-center py-8 text-grey"
};
const _hoisted_6 = {
  key: 3,
  class: "text-center py-8 text-grey"
};

const {ref: ref$1,computed,onMounted} = await importShared('vue');



const _sfc_main$1 = {
  __name: 'Cleanup',
  props: {
  api: { 
    type: [Object, Function],
    required: true,
  }
},
  setup(__props) {

const props = __props;

const orphanSubtitles = ref$1([]);
const totalFound = ref$1(0);
const cleanedCount = ref$1(0);
const selectedPaths = ref$1([]);
const scanning = ref$1(false);
const cleaning = ref$1(false);
const loading = ref$1(false);
const scanPaths = ref$1([]);
const selectedPathsList = ref$1([]);

const pathOptions = computed(() => {
  const options = [];
  if (scanPaths.value.length > 0) {
    options.push({ label: '全部媒体库路径', value: '__all__' });
    scanPaths.value.forEach((path, index) => {
      options.push({ label: path, value: path });
    });
  }
  return options
});

const headers = [
  { text: '', value: 'select', width: '5%' },
  { text: '文件路径', value: 'path', width: '60%' },
  { text: '大小', value: 'size', width: '15%' },
  { text: '修改时间', value: 'modified_time', width: '20%' }
];

const handlePathChange = (newVal) => {
  if (!newVal || newVal.length === 0) {
    selectedPathsList.value = ['__all__'];
  }
};

const getScanPaths = () => {
  if (!selectedPathsList.value || selectedPathsList.value.length === 0) {
    return scanPaths.value
  }
  if (selectedPathsList.value.includes('__all__')) {
    return scanPaths.value
  }
  return selectedPathsList.value
};

const scanOrphanSubtitles = async () => {
  scanning.value = true;
  selectedPaths.value = [];
  try {
    const paths = getScanPaths();
    const data = await props.api.get('plugin/DanmuTV/scan_orphan_subtitles', {
      params: { path: paths.join('\n') }
    });
    if (data && data.success) {
      orphanSubtitles.value = data.data.orphan_subtitles || [];
      totalFound.value = data.data.total_found || 0;
    }
  } catch (error) {
    console.error('扫描残留弹幕失败:', error);
  } finally {
    scanning.value = false;
  }
};

const fetchConfig = async () => {
  try {
    const data = await props.api.get('plugin/DanmuTV/config');
    if (data) {
      // /config 端点直接返回配置对象，没有 success/data 包装
      const path = data.path || '';
      scanPaths.value = path.split('\n').filter(p => p.trim());
      if (scanPaths.value.length > 0) {
        selectedPathsList.value = ['__all__'];
      }
    }
  } catch (error) {
    console.error('获取配置失败:', error);
  }
};

const cleanSelected = async () => {
  if (!selectedPaths.value.length) return
  cleaning.value = true;
  try {
    const data = await props.api.post('plugin/DanmuTV/clean_orphan_subtitles', selectedPaths.value);
    if (data && data.success) {
      cleanedCount.value += data.data.cleaned_count || 0;
      orphanSubtitles.value = orphanSubtitles.value.filter(item => !selectedPaths.value.includes(item.path));
      totalFound.value = orphanSubtitles.value.length;
      selectedPaths.value = [];
    }
  } catch (error) {
    console.error('清理选中字幕失败:', error);
  } finally {
    cleaning.value = false;
  }
};

const cleanAll = async () => {
  if (!orphanSubtitles.value.length) return
  if (!confirm('确定要删除所有找到的残留弹幕字幕文件吗？此操作不可恢复。')) {
    return
  }
  cleaning.value = true;
  try {
    const paths = orphanSubtitles.value.map(item => item.path);
    const data = await props.api.post('plugin/DanmuTV/clean_orphan_subtitles', paths);
    if (data && data.success) {
      cleanedCount.value += data.data.cleaned_count || 0;
      orphanSubtitles.value = [];
      totalFound.value = 0;
      selectedPaths.value = [];
    }
  } catch (error) {
    console.error('清理所有字幕失败:', error);
  } finally {
    cleaning.value = false;
  }
};

const selectAll = () => {
  if (selectedPaths.value.length === orphanSubtitles.value.length) {
    selectedPaths.value = [];
  } else {
    selectedPaths.value = orphanSubtitles.value.map(item => item.path);
  }
};

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
};

onMounted(() => {
  fetchConfig();
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$1("v-icon");
  const _component_v_card_title = _resolveComponent$1("v-card-title");
  const _component_v_alert = _resolveComponent$1("v-alert");
  const _component_v_col = _resolveComponent$1("v-col");
  const _component_v_row = _resolveComponent$1("v-row");
  const _component_v_select = _resolveComponent$1("v-select");
  const _component_v_btn = _resolveComponent$1("v-btn");
  const _component_v_spacer = _resolveComponent$1("v-spacer");
  const _component_v_chip = _resolveComponent$1("v-chip");
  const _component_v_progress_circular = _resolveComponent$1("v-progress-circular");
  const _component_v_checkbox = _resolveComponent$1("v-checkbox");
  const _component_v_data_table = _resolveComponent$1("v-data-table");
  const _component_v_card_text = _resolveComponent$1("v-card-text");
  const _component_v_card = _resolveComponent$1("v-card");
  const _component_v_container = _resolveComponent$1("v-container");

  return (_openBlock$1(), _createBlock$1(_component_v_container, {
    fluid: "",
    class: "pa-4"
  }, {
    default: _withCtx$1(() => [
      _createVNode$1(_component_v_card, {
        flat: "",
        class: "rounded border status-card"
      }, {
        default: _withCtx$1(() => [
          _createVNode$1(_component_v_card_title, { class: "text-caption d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
            default: _withCtx$1(() => [
              _createVNode$1(_component_v_icon, {
                icon: "mdi-delete-sweep",
                color: "error",
                size: "small",
                class: "mr-2"
              }),
              _cache[2] || (_cache[2] = _createTextVNode$1(" 残留弹幕字幕清理 ", -1))
            ]),
            _: 1
          }),
          _createVNode$1(_component_v_card_text, { class: "px-3 py-2" }, {
            default: _withCtx$1(() => [
              _createVNode$1(_component_v_row, { class: "mb-2" }, {
                default: _withCtx$1(() => [
                  _createVNode$1(_component_v_col, { cols: "12" }, {
                    default: _withCtx$1(() => [
                      _createVNode$1(_component_v_alert, {
                        type: "info",
                        density: "compact",
                        class: "text-caption",
                        variant: "tonal"
                      }, {
                        default: _withCtx$1(() => [
                          _createVNode$1(_component_v_icon, {
                            icon: "mdi-information",
                            size: "small",
                            class: "mr-1"
                          }),
                          _cache[3] || (_cache[3] = _createTextVNode$1(" 扫描并清理原视频已删除的残留弹幕字幕文件（.danmu.ass） ", -1))
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              }),
              _createVNode$1(_component_v_row, { class: "mb-3" }, {
                default: _withCtx$1(() => [
                  _createVNode$1(_component_v_col, {
                    cols: "12",
                    sm: "6"
                  }, {
                    default: _withCtx$1(() => [
                      _createVNode$1(_component_v_select, {
                        modelValue: selectedPathsList.value,
                        "onUpdate:modelValue": [
                          _cache[0] || (_cache[0] = $event => ((selectedPathsList).value = $event)),
                          handlePathChange
                        ],
                        items: pathOptions.value,
                        "item-title": "label",
                        "item-value": "value",
                        label: "选择扫描路径",
                        density: "compact",
                        variant: "outlined",
                        "hide-details": "",
                        multiple: ""
                      }, null, 8, ["modelValue", "items"])
                    ]),
                    _: 1
                  }),
                  _createVNode$1(_component_v_col, {
                    cols: "12",
                    sm: "6"
                  }, {
                    default: _withCtx$1(() => [
                      (!scanPaths.value.length)
                        ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_1$1, "请先在配置中设置媒体库路径"))
                        : _createCommentVNode$1("", true)
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              }),
              _createElementVNode$1("div", _hoisted_2, [
                _createVNode$1(_component_v_btn, {
                  color: "primary",
                  size: "small",
                  variant: "tonal",
                  "prepend-icon": "mdi-search",
                  onClick: scanOrphanSubtitles,
                  loading: scanning.value,
                  disabled: !scanPaths.value.length
                }, {
                  default: _withCtx$1(() => [...(_cache[4] || (_cache[4] = [
                    _createTextVNode$1(" 扫描残留弹幕 ", -1)
                  ]))]),
                  _: 1
                }, 8, ["loading", "disabled"]),
                _createVNode$1(_component_v_btn, {
                  color: "info",
                  size: "small",
                  variant: "tonal",
                  "prepend-icon": "mdi-check-all",
                  onClick: selectAll,
                  disabled: !orphanSubtitles.value.length
                }, {
                  default: _withCtx$1(() => [...(_cache[5] || (_cache[5] = [
                    _createTextVNode$1(" 全选 ", -1)
                  ]))]),
                  _: 1
                }, 8, ["disabled"]),
                _createVNode$1(_component_v_btn, {
                  color: "error",
                  size: "small",
                  variant: "tonal",
                  "prepend-icon": "mdi-delete",
                  onClick: cleanSelected,
                  disabled: !selectedPaths.value.length,
                  loading: cleaning.value
                }, {
                  default: _withCtx$1(() => [
                    _createTextVNode$1(" 清理选中 (" + _toDisplayString(selectedPaths.value.length) + ") ", 1)
                  ]),
                  _: 1
                }, 8, ["disabled", "loading"]),
                _createVNode$1(_component_v_btn, {
                  color: "error",
                  size: "small",
                  variant: "tonal",
                  "prepend-icon": "mdi-delete-forever",
                  onClick: cleanAll,
                  disabled: !orphanSubtitles.value.length,
                  loading: cleaning.value
                }, {
                  default: _withCtx$1(() => [...(_cache[6] || (_cache[6] = [
                    _createTextVNode$1(" 全部删除 ", -1)
                  ]))]),
                  _: 1
                }, 8, ["disabled", "loading"]),
                _createVNode$1(_component_v_spacer),
                (totalFound.value > 0)
                  ? (_openBlock$1(), _createBlock$1(_component_v_chip, {
                      key: 0,
                      size: "small",
                      variant: "tonal",
                      color: "primary"
                    }, {
                      default: _withCtx$1(() => [
                        _createTextVNode$1("找到: " + _toDisplayString(totalFound.value) + " 个", 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode$1("", true),
                (cleanedCount.value > 0)
                  ? (_openBlock$1(), _createBlock$1(_component_v_chip, {
                      key: 1,
                      size: "small",
                      variant: "tonal",
                      color: "success"
                    }, {
                      default: _withCtx$1(() => [
                        _createTextVNode$1("已清理: " + _toDisplayString(cleanedCount.value) + " 个", 1)
                      ]),
                      _: 1
                    }))
                  : _createCommentVNode$1("", true)
              ]),
              (scanning.value)
                ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_3, [
                    _createVNode$1(_component_v_progress_circular, {
                      indeterminate: "",
                      color: "primary",
                      size: "64"
                    }),
                    _cache[7] || (_cache[7] = _createElementVNode$1("p", { class: "mt-2" }, "正在扫描...", -1))
                  ]))
                : (_openBlock$1(), _createBlock$1(_component_v_data_table, {
                    key: 1,
                    headers: headers,
                    items: orphanSubtitles.value,
                    "items-per-page": 10,
                    loading: loading.value,
                    class: "elevation-1",
                    "hide-default-footer": ""
                  }, {
                    "item.select": _withCtx$1(({ item }) => [
                      _createVNode$1(_component_v_checkbox, {
                        value: item.path,
                        modelValue: selectedPaths.value,
                        "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((selectedPaths).value = $event)),
                        "hide-details": ""
                      }, null, 8, ["value", "modelValue"])
                    ]),
                    "item.path": _withCtx$1(({ item }) => [
                      _createElementVNode$1("div", {
                        class: "text-caption",
                        title: item.path
                      }, _toDisplayString(item.path), 9, _hoisted_4)
                    ]),
                    "item.size": _withCtx$1(({ item }) => [
                      _createTextVNode$1(_toDisplayString(formatSize(item.size)), 1)
                    ]),
                    "item.modified_time": _withCtx$1(({ item }) => [
                      _createTextVNode$1(_toDisplayString(item.modified_time), 1)
                    ]),
                    _: 1
                  }, 8, ["items", "loading"])),
              (!scanning.value && totalFound.value === 0 && !loading.value && scanPaths.value.length)
                ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_5, [
                    _createVNode$1(_component_v_icon, {
                      icon: "mdi-check-circle",
                      size: "48",
                      color: "success"
                    }),
                    _cache[8] || (_cache[8] = _createElementVNode$1("p", { class: "mt-2" }, "没有找到残留弹幕字幕文件", -1))
                  ]))
                : _createCommentVNode$1("", true),
              (!scanPaths.value.length && !scanning.value)
                ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_6, [
                    _createVNode$1(_component_v_icon, {
                      icon: "mdi-alert-circle",
                      size: "48",
                      color: "warning"
                    }),
                    _cache[9] || (_cache[9] = _createElementVNode$1("p", { class: "mt-2" }, "请先在配置中设置媒体库路径", -1))
                  ]))
                : _createCommentVNode$1("", true)
            ]),
            _: 1
          })
        ]),
        _: 1
      })
    ]),
    _: 1
  }))
}
}

};
const Cleanup = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-5312edb9"]]);

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,withCtx:_withCtx,createTextVNode:_createTextVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "plugin-page" };

const {ref,watch} = await importShared('vue');


const _sfc_main = {
  __name: 'Page',
  props: {
  api: { 
    type: [Object, Function],
    required: true,
  }
},
  emits: ['close', 'switch'],
  setup(__props, { emit: __emit }) {

const emit = __emit;

const activeTab = ref('dashboard');

const refreshDashboard = () => {
  if (activeTab.value === 'dashboard') {
    window.dispatchEvent(new Event('dashboard-refresh'));
  }
};

watch(activeTab, (newTab) => {
  if (newTab === 'dashboard') {
    refreshDashboard();
  }
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_tab = _resolveComponent("v-tab");
  const _component_v_tabs = _resolveComponent("v-tabs");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_divider = _resolveComponent("v-divider");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_card_actions = _resolveComponent("v-card-actions");
  const _component_v_card = _resolveComponent("v-card");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_v_card, {
      flat: "",
      class: "rounded border"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center px-3 py-2 bg-primary-lighten-5" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_icon, {
              icon: "mdi-video",
              class: "mr-2",
              color: "primary",
              size: "small"
            }),
            _cache[3] || (_cache[3] = _createElementVNode("span", null, "影视弹幕刮削", -1))
          ]),
          _: 1
        }),
        _createVNode(_component_v_tabs, {
          modelValue: activeTab.value,
          "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((activeTab).value = $event)),
          class: "px-3",
          centered: "",
          "background-color": "transparent",
          shrink: ""
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_tab, { value: "dashboard" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_icon, {
                  icon: "mdi-view-dashboard",
                  size: "small",
                  class: "mr-1"
                }),
                _cache[4] || (_cache[4] = _createTextVNode(" 仪表盘 ", -1))
              ]),
              _: 1
            }),
            _createVNode(_component_v_tab, { value: "browse" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_icon, {
                  icon: "mdi-folder",
                  size: "small",
                  class: "mr-1"
                }),
                _cache[5] || (_cache[5] = _createTextVNode(" 目录浏览 ", -1))
              ]),
              _: 1
            }),
            _createVNode(_component_v_tab, { value: "retry" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_icon, {
                  icon: "mdi-alert-circle-outline",
                  size: "small",
                  class: "mr-1"
                }),
                _cache[6] || (_cache[6] = _createTextVNode(" 重试任务 ", -1))
              ]),
              _: 1
            }),
            _createVNode(_component_v_tab, { value: "history" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_icon, {
                  icon: "mdi-history",
                  size: "small",
                  class: "mr-1"
                }),
                _cache[7] || (_cache[7] = _createTextVNode(" 历史记录 ", -1))
              ]),
              _: 1
            }),
            _createVNode(_component_v_tab, { value: "cleanup" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_icon, {
                  icon: "mdi-delete-sweep",
                  size: "small",
                  class: "mr-1"
                }),
                _cache[8] || (_cache[8] = _createTextVNode(" 清理 ", -1))
              ]),
              _: 1
            })
          ]),
          _: 1
        }, 8, ["modelValue"]),
        _createVNode(_component_v_card_text, { class: "p-0" }, {
          default: _withCtx(() => [
            (activeTab.value === 'dashboard')
              ? (_openBlock(), _createBlock(Dashboard, {
                  key: 0,
                  api: __props.api
                }, null, 8, ["api"]))
              : (activeTab.value === 'browse')
                ? (_openBlock(), _createBlock(BrowseView, {
                    key: 1,
                    api: __props.api,
                    onRefresh: refreshDashboard
                  }, null, 8, ["api"]))
                : (activeTab.value === 'retry')
                  ? (_openBlock(), _createBlock(RetryTasks, {
                      key: 2,
                      api: __props.api
                    }, null, 8, ["api"]))
                  : (activeTab.value === 'history')
                    ? (_openBlock(), _createBlock(History, {
                        key: 3,
                        api: __props.api
                      }, null, 8, ["api"]))
                    : (activeTab.value === 'cleanup')
                      ? (_openBlock(), _createBlock(Cleanup, {
                          key: 4,
                          api: __props.api
                        }, null, 8, ["api"]))
                      : _createCommentVNode("", true)
          ]),
          _: 1
        }),
        _createVNode(_component_v_divider),
        _createVNode(_component_v_card_actions, { class: "px-2 py-1" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_btn, {
              color: "info",
              onClick: _cache[1] || (_cache[1] = $event => (emit('switch'))),
              "prepend-icon": "mdi-cog",
              variant: "text",
              size: "small"
            }, {
              default: _withCtx(() => [...(_cache[9] || (_cache[9] = [
                _createTextVNode("配置", -1)
              ]))]),
              _: 1
            }),
            _createVNode(_component_v_spacer),
            _createVNode(_component_v_btn, {
              color: "grey",
              onClick: _cache[2] || (_cache[2] = $event => (emit('close'))),
              "prepend-icon": "mdi-close",
              variant: "text",
              size: "small"
            }, {
              default: _withCtx(() => [...(_cache[10] || (_cache[10] = [
                _createTextVNode("关闭", -1)
              ]))]),
              _: 1
            })
          ]),
          _: 1
        })
      ]),
      _: 1
    })
  ]))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-0da56888"]]);

export { Page as default };
