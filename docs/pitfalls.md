# 踩坑记录（pitfalls）

> 只记录非显而易见、未来可能再次踩到的问题与正确绕开姿势。通用知识不写。
> 更新时机：遇到这类问题时。格式：现象/原因/解决/备注。

## danmu-api 新版默认限流 3 次/分钟，客户端不节流会批量 429
- 现象：升级内置 danmu-api（logvar/danmu-api）后批量刮削频繁 429、文件大量进重试队列；外接新版 danmu-api 的用户同样遇到。
- 原因：danmu-api 引入 `RATE_LIMIT_MAX_REQUESTS`（1分钟内最大请求次数，默认 3，0=不限流），而本项目原客户端节流为 1s 间隔（60 次/分钟），远超限额；且健康检查 `/api/logs`、前端搜索也各占额度。
- 解决：客户端节流改为配置项 `api_request_interval`（默认 21s ≈ 3 次/分钟，每个文件 2 次请求约 1 文件/分钟），所有请求统一走 `_throttle_request()`；内置 compose 通过环境变量配对恢复原速——fndanmutv 注入 `DANMUTV_API_REQUEST_INTERVAL=1`（1s 间隔 ≤60 次/分），danmu-api 设 `RATE_LIMIT_MAX_REQUESTS=120`（可信内网，留一倍余量，仅防失控）。
- 备注：环境变量只在首次启动或旧配置缺 `api_request_interval` 键时生效，UI 保存后 DB 值优先；想更快必须先调大 danmu-api 端 `RATE_LIMIT_MAX_REQUESTS`（或设 0），再把间隔调小，仅调小间隔会重新触发 429。

## danmu API 地址只支持"单段路径"形式的 token
- 现象：配置了带多级路径的 danmu API 地址后，所有弹幕请求 404/打不到正确端点。
- 原因：[danmu_generator.py](../backend/app/danmu_generator.py) 的 `DanmuAPI.set_api_url()` 用正则 `^(https?://[^/]+)(/[^/]+)?$` 拆地址——`scheme://host` 之后只接受**一个无斜杠路径段**作为 token（如 `http://host:9321/xxxx`），再拼回 `{base}/{token}/api/v2/...`。超过一段（`/a/b`）直接整体当 base、token 置空。
- 解决：danmu-api 地址只填 `http://主机:9321` 或 `http://主机:9321/单段token`；反代若挂在子路径下，需自行把上游映射成单段。
- 备注：内置 compose 的 danmu-api 无 token，默认值 `http://danmu-api:9321` 即可，不要手滑加尾斜杠（代码会 `rstrip('/')`，但仍应规范填写）。

## 历史"详情只留 20 条"是注释/spec 的说法，代码并未裁剪
- 现象：spec 与 `_append_history()` 注释都写"详情只在最近 20 条概要中保留"，但数据库里 100 条概要行的 `details_json` 都可能有值。
- 原因：[danmu_service.py](../backend/app/services/danmu_service.py) 的 `_append_history()` 只把概要裁剪到 100 条，没有按位置删 details；"20"实际只是 `GET /history` 的默认 `page_size`。
- 解决：以代码现状为准（概要 100 条、details 随行存储，靠 `include_details` 与分页控制返回）。要实现 spec 语义需另加裁剪逻辑，改的时候同步修掉第 465 行注释。
- 备注：单文件失败详情始终记录；批量详情仅在 `enable_history_details=true` 时记录（见 [DATA_MODEL.md](DATA_MODEL.md)）。

## 每次写历史都全表重写 global_history
- 现象：刮削大批量媒体时历史表写入有放大效应。
- 原因：`_append_history()` 落库方式是 `clear_global_history()` 后把内存中最多 100 条逐条 `insert_history_record()`（代码注释自述"简单起见重写历史表"）。
- 解决：历史被限定在 100 条，量级可控，暂不优化；若未来放宽上限，需改成增量插入 + 定向删除。
- 备注：同函数的内存裁剪与落库在 `_history_lock` 内，与读取互斥。

## 孤儿弹幕扫描只能按"已知命名规格"精确识别，不能用子串匹配
- 现象：清理 Tab 把 Jellyfin/Emby 弹幕插件生成的 `剧集.chs[YoukuID_danmu].ass` 大量误报为孤儿，而同名 .mp4 就在旁边。
- 原因：旧逻辑只判断文件名含 `"danmu"`，再 replace `.danmu.chs`/`.danmu` 还原视频名——插件的 `[SourceID_danmu]` 标记剥不掉，还原出的 basename 带 `.chs[YoukuID_danmu]`，同伴查找必然失败；`.withDanmu.ass` 同理（同伴是原字幕不是视频），且媒体扩展名只查 mp4/mkv/strm 三种，.ts/.avi 等也会误报。
- 解决：[scan_service.py](../backend/app/services/scan_service.py) 的 `_classify_danmu_ass()` 按三类规格精确分类——`.danmu.chs.ass`（同伴=媒体）、`.withDanmu.ass`（同伴=ass/ssa/srt 原字幕）、`[xxxx_danmu]` 标记（正则剥标记+Jellyfin 语言后缀后同伴=媒体）；同伴扩展名统一用 `MEDIA_EXTENSIONS`，同目录比对走小写集合以兼容大写扩展名。
- 备注：`[xxxx_danmu]` 是 cxfksword jellyfin-plugin-danmu / fengymi emby-plugin-danmu 的命名（来源如 YoukuID、BiliBiliId），非本程序产物，但用户库中可能共存，所以纳入识别而非忽略。

## QEMU 模拟 arm64 构建后容器一直 unhealthy
- 现象：`docker buildx --platform linux/arm64 --load` + QEMU 运行，容器健康检查失败残留 unhealthy。
- 原因：QEMU 下 `import app.main` 冷启动约 104s，远超 HEALTHCHECK 的 `--start-period=10s --timeout=5s`；真实 arm64 硬件无此问题。
- 解决：不要为模拟环境放宽健康检查参数；arm64 验证只看冒烟结果（见 [decisions.md](decisions.md) 2026-09-13 条）。
- 备注：启用 containerd image store 时，跨架构 `--load` 后**未运行过**的镜像只显示 content size（曾见 arm64 显示 87.5MB），运行一次解包后才显示逻辑体积，勿误判为镜像不完整。
