# DanmuTV 目录结构与模块职责（PROJECT_STRUCTURE）

> 版本：v1.0 ｜ 只记录目录放置理由与模块边界。具体接口见 [API.md](API.md)，表结构见 [DATA_MODEL.md](DATA_MODEL.md)。

## 1. 顶层目录

```
fndanmutv/
├── backend/                  FastAPI 后端（Python 3.12，conda 环境 danmu）
│   ├── app/
│   └── requirements.txt
├── frontend/                 Vue3 + Vite + Vuetify3 SPA（构建产物 dist/ 由后端托管）
│   ├── src/
│   └── package.json
├── fn-app/                   绿联云（UGOS）应用打包工程（fpk/manifest/wizard/图标）
├── docs/                     项目文档（本目录）
├── references/               只读参考代码与静态 ffmpeg（禁止修改，不随镜像/仓库分发二进制）
├── .trae/                    Trae IDE 规则、spec、迁移方案
├── Dockerfile                多阶段镜像构建
├── docker-compose.yml        完整版（fndanmutv + 内置 danmu-api）
├── docker-compose.standalone.yml  独立版（外部 danmu-api，host 网络）
├── dev.sh                    本地开发环境管理（start/stop/restart/status/logs）
└── README.md
```

- `references/` 是只读迁移来源，迁移 = 复制 + 改造，勿原地改；`references/ffmpeg/` 下的静态二进制需构建前手动下载（见 [CONTRIBUTING.md](CONTRIBUTING.md)）。
- 代码只能落在 `backend/app/` 与 `frontend/src/`；不新建平行的后端/前端目录。

## 2. backend/app 模块职责

```
backend/app/
├── main.py               FastAPI 应用入口：lifespan（日志/建库/组装 DanmuService+Scheduler）、
│                         CORS、路由注册、/health、StaticFiles 与 SPA fallback
├── config.py             pydantic-settings 配置（DANMUTV_ 前缀 / ADMIN_TOKEN / .env），
│                         负责 data 目录创建、缺省随机 Token、DB 路径
├── models.py             Pydantic 模型：ApiResponse / AppConfig（全部配置项+默认值）/
│                         AnimeInfo / ManualMatchRequest
├── database.py           sqlite3 数据访问：建表（CREATE IF NOT EXISTS + 兼容 ALTER）、
│                         连接/WAL/写锁、config/retry/manual/directory/history 全部 CRUD
├── deps.py               FastAPI 依赖：require_token（Bearer 鉴权）、get_service（取 app.state.svc）
├── timeutil.py           时间工具
├── logging_config.py     标准 logging 配置
├── danmu_generator.py    核心引擎（约 1600 行，迁移自插件）：
│                         DanmuAPI / DanmuConverter / SubtitleProcessor /
│                         StrmProcessor / danmu_generator() 单例函数
├── api/
│   ├── __init__.py
│   └── routes.py         全部 HTTP 路由（public_router 免鉴权 + router 鉴权），薄路由层
└── services/
    ├── __init__.py
    ├── danmu_service.py  DanmuService：业务编排与全部运行时状态（~1200 行）
    ├── scan_service.py   目录树扫描 / 统计 / 孤儿字幕（模块级函数）
    ├── media_parser.py   纯文件名解析：ParsedMedia(title/season/episode/is_movie/is_strm)
    └── scheduler.py      唯一 APScheduler 实例封装：重试 job + 自动刮削 job
```

### 边界约束

- 路由层禁止写 SQL / 扫描文件 / 复杂业务；只做参数解析、调 service、包装 `ApiResponse`。
- `media_parser` 与 `DanmuConverter` 是纯逻辑，不碰 DB。
- 定时任务只能经 `services/scheduler.py` 的全局唯一 scheduler；禁止在别处 `BackgroundScheduler()`。
- 配置字段的唯一来源是 `models.AppConfig`；`GET /config` 返回其落库后的裸 dict，新增配置项改这里。

## 3. frontend/src 结构

```
frontend/src/
├── main.js               Vue + Vuetify 初始化
├── App.vue               根组件：Page/Config 切换、登录态、全局 snackbar 通知
├── api/
│   └── index.js          唯一 axios 实例（baseURL=/api）：请求注入 Bearer Token、
│                         401/403 拦截、响应解包 res.data、get 的 query 参数兼容
└── components/
    ├── Page.vue          主框架：顶栏（登录/配置/登出）+ 5 个 Tab + 登录对话框
    ├── Dashboard.vue     仪表盘（插件状态/统计/最近运行/刮削进度）
    ├── BrowseView.vue    目录浏览（目录树、手动匹配对话框、刮削/清字幕）
    ├── RetryTasks.vue    重试任务列表（手动重试/移除/清空）
    ├── History.vue       历史记录（分页、详情展开、清空）
    ├── Cleanup.vue       残留弹幕字幕清理（扫描/选择/删除）
    └── Config.vue        配置页（基本设置/弹幕参数/预设方案/媒体库路径）
```

### 前端链路约定

- 所有接口调用必须经 `src/api/index.js`，禁止组件内裸 `fetch` / 新建 axios 实例。
- 禁止 `props.api`、postMessage、iframe、Module Federation / `remoteEntry.js` 残留。
- 接口路径写 `/xxx`（baseURL 已含 `/api`）。

## 4. 核心数据流

**批量刮削**：
`BrowseView/定时job` → `GET /api/scrape_directory` → `DanmuService.scrape_directory`
（收集文件、增量过滤、起后台线程）→ 逐文件 `generate_single`
→ `media_parser.parse_media` + `DanmuAPI`（手动匹配/文件名匹配→下载评论）
→ `DanmuConverter` 写 `.danmu.chs.ass` → `SubtitleProcessor` 找/提/合并字幕
→ 更新进度/重试/历史/目录记录；前端轮询 `/api/status` 与 `/api/full_status`。

**配置变更**：
`Config.vue` → `POST /api/config`（裸 dict）→ 三层合并落库 → `DanmuAPI.set_api_url`
→ `scheduler.reschedule`（增删重试/自动扫描 job）→ 返回最新配置。
