# DanmuTV 开发规则总则（DEVELOPMENT_RULES）

> 版本：v1.0 ｜ 本文档对所有开发任务永久生效；日常轻量任务按仓库根目录 `开发规则.md`（精简版）执行，冲突时以本文为准。
> 配套交付自检见 §10（提交前逐项确认）。

## 1. 工作节奏与环境

1. 需求来源以 `.trae/specs/extract-standalone-docker-app/` 下 spec/tasks/checklist 为准；一次只做一个明确任务，不做 spec 外改动，完成立即勾选。
2. 后端 Python 3.12，所有 python/pip 走 `conda run -n danmu ...`；前端 Node 18+。
3. 日常开发一律用 `./dev.sh`（`start|stop|restart|status` 控前后端，`logs [backend|frontend]` 查日志）：前端 http://localhost:8017（Vite 代理 `/api` 到后端），后端 http://localhost:8021，健康检查 `/health`；本地固定 Token `dev-token`（`backend/.env`，该文件不入库）。
4. 功能验证**禁止反复 `docker compose up --build`**；镜像/编排验证留到部署相关改动时一次完成。
5. 本机需可执行 `ffmpeg` / `ffprobe`；镜像用静态二进制需构建前下载（见 [CONTRIBUTING.md](CONTRIBUTING.md)）。

## 2. 代码位置

- 后端只放 `backend/app/`，前端只放 `frontend/src/`。
- `references/`（含 AbulmShelf、插件原码、ffmpeg 二进制目录）只读；迁移 = 复制 + 改造，禁止原地修改。
- 生成物不入库：`data/`、`.env`、`*.db`、`node_modules/`、`dist/`、`__pycache__/`。

## 3. 红线（违反必返工）

### 后端

- 禁止任何 MoviePilot 依赖：`from app...`、`app.log`、`MetaInfo`、`MediaChain`、`MediaType`、`save_data/get_data/update_config`、`schemas.Response`、`_PluginBase`、事件管理器等。
- 持久化只用 SQLite（`database.py`）；禁止引入其他 DB/ORM。
- 定时任务只用 `services/scheduler.py` 中全局唯一的 APScheduler（单 worker，`max_instances=1, coalesce=True`），禁止重复 `new BackgroundScheduler()`。
- API 统一 `/api` 前缀 + Bearer Token；新增业务路由挂到带鉴权的 `router`，只读公开接口才挂 `public_router`。
- 保持既有响应契约：`GET /config` 返**裸 dict**；`POST /clean_orphan_subtitles` 收**裸数组**；其余用 `ApiResponse{success,message,data}`，失败用 HTTP 200 + `success:false`（认证错误才 401/403）。
- 路由层保持薄：不写 SQL、不扫描文件、不内联复杂业务。
- 新增配置项必须改 `models.AppConfig`（默认值），不要散落硬编码。

### 前端

- 禁止 `props.api`、postMessage、iframe、Module Federation / `remoteEntry.js`、vuetify-filter 残留。
- 所有接口走 [src/api/index.js](../frontend/src/api/index.js) 唯一 axios 实例，路径写 `/xxx`；禁止组件裸 fetch / 自造实例。
- 不自行发明与 API.md 不一致的数据结构；接口变更必须双端同步并回写 [API.md](API.md)。

### 通用

- 不硬编码 Token/密钥；未配置 Token 时由后端随机生成。
- 弹幕/字幕写回视频同目录；容器内路径与 Web UI 配置路径必须一致，媒体卷 `:rw`。

## 4. 分层与依赖

```
routes → services（danmu_service / scan_service / scheduler）
              → danmu_generator（引擎：DanmuAPI / DanmuConverter / SubtitleProcessor）
              → database（sqlite3）
media_parser：纯函数，不碰 DB/网络
```

- `DanmuService` 是唯一持有运行时状态（配置/进度/重试/匹配缓存/历史）的单例，在 `main.py` lifespan 组装并挂到 `app.state.svc`，经 `deps.get_service` 获取。
- 引擎 `danmu_generator.py` 保持与上游插件逻辑一致，仅在必要时改造（如日志导入）；业务规则不要下沉进引擎。

## 5. 关键业务规则（改动时勿破坏）

- 有效弹幕判定：`<base>.danmu.chs.ass` 存在且 `Dialogue:` 行数 ≥ 100（`DanmuService.MIN_DANMU_COUNT`）。
- 重试：退避 `[5,30,60,120,240,480]` 分钟、最多 10 次；`rate_limit ≥30`、`no_match ≥60`、`no_data ≥15` 分钟下限；429 立即中断批量/本轮重试。
- commentId = `animeId*10000 + 集数`；匹配优先级：文件级手动匹配 → 目录 `.dandan.anime.json`（含集数偏移）→ 文件名 match。
- 批量串行：每文件间隔 0.5s；同时只允许一个批量任务；中止在当前文件完成后生效。
- 递归收集"最浅层优先"（某层有媒体即不再下钻，最深 6 层，跳过点号目录）。
- 媒体扩展名白名单：`.mp4 .mkv .avi .mov .wmv .flv .ts .m4v`（+ 启用时 `.strm`）。

## 6. 数据与迁移

- 建表只用 `CREATE TABLE IF NOT EXISTS`；旧库变更用 `ALTER TABLE ADD COLUMN`（失败忽略），只增不改不删。
- 复杂状态以 JSON 文本列存储（`*_json`，`ensure_ascii=False`）；历史概要保留 100 条。
- 表结构变更必须同步 [DATA_MODEL.md](DATA_MODEL.md)。

## 7. 省 token 行为约束

- 动手前先查本文档地图与已有实现；检索即取证：不整仓通读、>1500 行文件用关键词检索 + 分段读、同一搜索不重复、同任务搜索 ≤3 轮。
- 小步改、精确小 diff；不无意义重构；新依赖先说理由并同步 `requirements.txt` / `package.json` / Dockerfile；需求含糊先问清。
- 注释精简，不批量造测试。

## 8. 文档维护

| 变化 | 更新文档 |
| --- | --- |
| 接口/响应/错误码 | [API.md](API.md)（唯一契约） |
| 表结构/配置项 | [DATA_MODEL.md](DATA_MODEL.md) |
| 架构/目录/运行方式 | [ARCHITECTURE.md](ARCHITECTURE.md)、[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)、[context.md](context.md) |
| 页面/交互 | [UI_DESIGN.md](UI_DESIGN.md) |
| 重要选型 | [decisions.md](decisions.md) |
| 非显而易见的坑 | [pitfalls.md](pitfalls.md) |
| 专属约定/技术债 | [conventions.md](conventions.md) |

知识四件套只写项目独有、AI 无法从通用知识推断的内容，不灌水、不重复 spec。

## 9. 分层验证（提交前）

1. 后端冒烟导入：`conda run -n danmu python -c "import app.main"`（在 `backend/` 下）。
2. 前端构建：`cd frontend && npm run build`——dist 正常、无 `remoteEntry.js`、CSS 含 `.v-`/`.mdi-`。
3. 接口：无 Token 401/403、带 Token 200（如 `GET /api/auth/verify`、`GET /api/config`）。
4. 涉 Docker：`docker compose build`（需要先备好 `references/ffmpeg/` 静态二进制）。
5. 交付摘要 = 修改范围 + 验证结果。

## 10. 交付自检清单

> 完成任务前逐项确认；细节以 spec/tasks/checklist 为准，不在此重复。

- [ ] spec 对应明确、未做 spec 外改动；tasks.md / checklist.md 已勾选。
- [ ] 代码位置正确（backend/app 或 frontend/src）；未碰 references/。
- [ ] 无 MoviePilot 残留；持久化走 SQLite；定时任务走统一 APScheduler。
- [ ] API 前缀 `/api` + Bearer Token；契约未破坏（`/config` 裸 dict、`clean_orphan_subtitles` 裸数组）。
- [ ] 前端无 props.api / postMessage / iframe / Module Federation 残留；接口走 `src/api/index.js`。
- [ ] 环境正确：python/pip 用 conda `danmu`；前端 Node 18+。
- [ ] 新增依赖已同步 requirements.txt / package.json / Dockerfile。
- [ ] 验证通过：后端冒烟导入；前端 `npm run build`（dist 正常、无 remoteEntry.js、CSS 含 `.v-`/`.mdi-`）；接口 401/200；涉 Docker 时 compose build。
- [ ] 项目专属知识已沉淀 docs/（架构→context、选型→decisions、踩坑→pitfalls、约定/技术债→conventions），未写通用常识。
- [ ] 无硬编码密钥；.gitignore 覆盖 data/、.env、*.db、node_modules、dist、__pycache__。
- [ ] 遵循 Git 规范；一次提交一件事；不提交生成物与敏感文件。
