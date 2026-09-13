# 项目背景与现状（context）

> 本文只回答"这是什么项目、现在到哪一步"。架构细节看 [ARCHITECTURE.md](ARCHITECTURE.md)，目录看 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)。
> 更新时机：项目定位、交付范围、开发阶段变化时。

## 文档导航
| 想了解 | 看哪篇 |
| --- | --- |
| 做什么、不做什么 | [PRD.md](PRD.md) |
| 技术架构与运行机制 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 目录与模块职责 | [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) |
| 数据库表与配置项 | [DATA_MODEL.md](DATA_MODEL.md) |
| HTTP 接口契约 | [API.md](API.md) |
| 前端页面与交互 | [UI_DESIGN.md](UI_DESIGN.md) |
| 开发总则与自检 | [DEVELOPMENT_RULES.md](DEVELOPMENT_RULES.md)、[CONTRIBUTING.md](CONTRIBUTING.md) |
| 选型原因 / 踩坑 / 约定 | [decisions.md](decisions.md) / [pitfalls.md](pitfalls.md) / [conventions.md](conventions.md) |

## 背景
- DanmuTV 原为 MoviePilot V2 插件，本仓库将其抽离为**可独立部署的 Docker 全栈应用**：FastAPI 后端 + Vue3 SPA + 内置 danmu-api，一条 compose 启动。
- 需求来源与验收标准以 `.trae/specs/extract-standalone-docker-app/` 下 spec/tasks/checklist 为准；迁移设计见 `.trae/documents/standalone-docker-migration.md`。
- 插件原代码在 `references/` 下**只读保留**，迁移采用复制 + 改造，不在原地修改。

## 现状
- 已交付独立应用：27 个 `/api` 端点（Bearer Token 鉴权）、5 张 SQLite 表、APScheduler 重试/自动扫描、5 Tab 前端 SPA、多阶段 Dockerfile（amd64/arm64，镜像约 300MB）。
- 核心弹幕引擎 [danmu_generator.py](../backend/app/danmu_generator.py)（约 1600 行）由插件代码迁移而来，是全项目唯一的大文件，业务规则集中在其中，改动前先读 [ARCHITECTURE.md](ARCHITECTURE.md) 的刮削状态机一节。
- 运行数据：`DANMUTV_DATA_DIR`（默认 `/data`）下 `danmutv.db`；弹幕/字幕写回视频同目录，不另建媒体库副本。
- 开发阶段与勾选状态以 spec 的 tasks.md/checklist.md 为准，本文不维护进度明细。
