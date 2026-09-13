# DanmuTV 技术架构（ARCHITECTURE）

> 版本：v1.0 ｜ 记录系统分层、关键技术选型与运行机制。项目背景见 [PRD.md](PRD.md)，目录边界见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)。

## 1. 总览

单容器全栈应用：FastAPI 同时提供 `/api/*` 接口与前端 SPA 静态资源；外部依赖一个 danmu-api（弹弹 play 兼容）后端，可由 compose 内置或外部提供。

```
浏览器 (Vue3 SPA)
   │  /api/*  (Authorization: Bearer <token>)
   ▼
FastAPI (uvicorn) ── APScheduler（唯一实例，后台线程）
   │
   ├── routes.py        路由层：参数解析 + 调 Service + 包装响应
   ├── services/
   │     danmu_service.py   业务编排（刮削状态机/重试/历史/手动匹配/配置）
   │     scan_service.py    目录扫描/统计/孤儿字幕（模块级函数）
   │     media_parser.py    纯文件名正则解析（剧名/季/集/电影/.strm）
   │     scheduler.py       定时任务（5 分钟重试 + 可配间隔自动刮削）
   ├── danmu_generator.py  核心引擎（danmu-api 客户端 / ASS 转换 / 字幕处理）
   └── database.py        sqlite3 数据访问（5 张表）
                │
                ▼
        DANMU_DATA_DIR/danmutv.db（默认 /data）

danmu_service ──HTTP──▶ danmu-api (/api/v2/match|search|comment, /api/logs)
danmu_generator ──子进程──▶ ffmpeg / ffprobe（时长/分辨率/内嵌字幕提取）
```

## 2. 技术选型

| 层 | 选型 | 理由 / 约束 |
| --- | --- | --- |
| Web 框架 | FastAPI + Uvicorn（Python 3.12） | 替代 MoviePilot 插件 API；轻量，自带校验与 OpenAPI |
| 数据校验 | Pydantic v2（pydantic-settings） | `ApiResponse` / `AppConfig` / `ManualMatchRequest`；环境变量统一前缀 `DANMUTV_` |
| 持久化 | 标准库 sqlite3 + WAL | 零外部依赖；单例连接随开随关，写操作经进程级 `_write_lock` 串行化，避免 `database is locked` |
| 定时任务 | APScheduler BackgroundScheduler | 全应用唯一实例（`app.state.scheduler`），`max_instances=1, coalesce=True`；保存配置后动态 reschedule |
| 前端 | Vue 3（`<script setup>`）+ Vite + Vuetify 3 + axios | 从 Module Federation 改为普通 SPA；接口统一走 `src/api/index.js` |
| 媒体识别 | 纯文件名正则（`media_parser.py` + 引擎内解析） | 不依赖 TMDB；SxxExx / Exx / .NN. / 第x集话话期回 |
| 字幕工具 | 静态 ffmpeg / ffprobe | 时长、分辨率、中文内嵌字幕提取；不随 git 分发，构建前下载（见 [CONTRIBUTING.md](CONTRIBUTING.md)） |
| 部署 | 多阶段 Dockerfile + docker compose | Node 构建前端 → python:3.12-slim 运行；镜像瘦身记录见 [decisions.md](decisions.md) |

## 3. 后端分层与依赖方向

```
routes（API 层）→ services（业务层）→ danmu_generator（引擎层）
                                     → database（数据访问层）
routes ── deps.get_service ── app.state.svc（lifespan 中组装的 DanmuService 单例）
```

- **routes.py 不写业务**：解析 Query/Body、调用 service、用 `ApiResponse.ok/fail` 包装。例外是两个历史契约（见 [API.md](API.md) §契约特例）。
- **DanmuService** 持有全部运行时状态：配置缓存、刮削进度与锁、重试队列、手动匹配缓存、历史记录；构造在 `lifespan` 中完成并注入 scheduler。
- **danmu_generator.py 是无业务状态的引擎**：HTTP 客户端类 `DanmuAPI`（含进程级限流状态）、`DanmuConverter`（弹幕→ASS）、`SubtitleProcessor`（字幕提取/合并）、`StrmProcessor` 与单例函数 `danmu_generator(...)`。从 MoviePilot 插件近乎原样迁移，仅日志改为标准 logging。
- **media_parser 是纯函数模块**，不碰数据库与网络。

## 4. 请求鉴权

- `public_router`（免鉴权）：`GET /api/status`、`GET /api/full_status`（仪表盘只读）。
- `router`（`dependencies=[Depends(require_token)]`）：其余全部 `/api/*`。
- `require_token`（[deps.py](../backend/app/deps.py)）：未配置 token 时直接放行；否则要求 `Authorization: Bearer <token>`，缺失 → 401，错误 → 403。
- 未配置 `DANMUTV_TOKEN` / `ADMIN_TOKEN` 时启动自动生成随机 Token 并打印到日志（重启变化）；`ADMIN_TOKEN` 优先级更高。
- 前端 axios 拦截器统一注入 Token；收到 401/403 清除本地 Token 并派发 `auth:unauthorized` 事件回到登录态。

## 5. 刮削状态机与并发

- 全局**单批量任务**：`_scrape_lock` 检查 `_scrape_progress.running`，重复请求报错。
- 进度结构：`{running,total,processed,success,failed,current_file,duration,auto_scrape}`，`GET /api/status` 轮询；运行中 `duration` 实时计算。
- 后台 daemon 线程串行处理：每文件前置检查中止标志 → 调 `generate_single` → 计数 → `time.sleep(0.5)`；429 时剩余文件不再请求、直接以 `rate_limit` 入重试队列并中断本轮。
- 结束（finally）：写批量历史、按公共前缀目录更新 `directory_records`、复位状态。
- 单文件去重：`_inflight_files` 集合防止同一文件并发重复刮削。

## 6. 限流与重试（两级）

1. **引擎级**：`DanmuAPI` 进程变量 `_rate_limit_until` + 全局请求锁（最小间隔 `api_request_interval` 配置，默认 21s ≈ 3 次/分钟，0=不限；可用环境变量 `DANMUTV_API_REQUEST_INTERVAL` 注入默认值；match/comment、健康检查、前端搜索统一走 `_throttle_request()` 排队）；match/comment 遇 429 优先读取响应 `Retry-After` 头（钳制 1~3600s），无头时本地指数退避 `max(30s, 节流间隔) × 2^retry`（默认 30/60/120/240s，最多 4 次），并抬高全局冷却时间。该默认值对齐 danmu-api 新版 `RATE_LIMIT_MAX_REQUESTS`（1分钟内最大请求次数，默认 3，0=不限流）；完整版 compose 将其设为 120 并注入客户端间隔 1s 恢复原速。
2. **业务级**：失败文件入 `retry_tasks`，退避序列 `[5,30,60,120,240,480]` 分钟（超 6 次封顶 480），错误类型设下限：`rate_limit ≥30`、`no_match ≥60`、`no_data ≥15` 分钟；达 10 次放弃删记录。APScheduler 每 5 分钟调 `process_retry_tasks`（同步、仅处理到期任务，遇 429 提前结束本轮）。

## 7. 定时任务

| Job id | 触发 | 开关 | 行为 |
| --- | --- | --- | --- |
| `danmutv_retry` | 固定每 5 分钟 | `enable_retry_task`（默认开） | 处理到期重试任务 |
| `danmutv_auto_scan` | `auto_scrape_interval` 秒（默认 3600，下限 60） | `auto_scrape`（默认关） | 对配置的多路径递归刮削，模式取 `auto_scrape_mode`（incremental/full） |

保存配置时 `scheduler.reschedule(config)` 增删/重排 job，不重启进程。

## 8. 静态资源与 SPA

- `frontend_dist`（默认 `frontend/dist`，容器内 `/app/static`）存在时：挂载 `/assets`，注册通配路由 `/{full_path}`：`/api/*` 返 404；dist 下存在的真实文件直接返回；其余回退 `index.html`。
- 目录不存在（本地后端开发模式）跳过挂载，前端由 Vite dev server 提供并代理 `/api`。

## 9. 数据与文件产物

- SQLite：`$DANMUTV_DATA_DIR/danmutv.db`，WAL 模式；表结构见 [DATA_MODEL.md](DATA_MODEL.md)。
- 媒体目录写回文件（与视频同目录）：
  - `<base>.danmu.chs.ass` 弹幕字幕；
  - `<字幕主名>.withDanmu.ass` 合并字幕（UTF-8 BOM，原字幕不改）；
  - `.dandan.anime.json` 目录级手动匹配。
- 容器路径与 Web UI 显示路径必须一致（如都为 `/media/...`），媒体卷必须 `:rw`。
