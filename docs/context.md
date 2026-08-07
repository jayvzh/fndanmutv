# 项目背景与现状（context）

> 仅记录项目独有信息：背景、架构、现状、关键环境。通用知识不写。
> 更新时机：架构调整、目录布局变化、关键依赖/运行方式变更时。

## 背景
- DanmuTV 原为 MoviePilot V2 插件，本仓库将其抽离为可独立部署的 Docker 全栈应用。
- 需求来源与细节以 `.trae/specs/extract-standalone-docker-app/` 下 spec/tasks/checklist 为准。

## 架构
- 后端：`backend/app/`（FastAPI + APScheduler + SQLite），核心引擎 `danmu_generator.py`。
- 前端：`frontend/src/`（Vue3 + Vite + Vuetify3 SPA），构建产物由后端 StaticFiles 托管。
- 参考代码：`references/.../danmutv/` 只读，迁移时复制改造，不在原地修改。
- 部署：根目录多阶段 Dockerfile + docker-compose.yml（danmutv + 可选 danmu-api）。

## 现状
- 开发阶段：按 spec 的 Task 1~12 推进，完成情况见 tasks.md/checklist.md。
- 运行数据：`DANMUTV_DATA_DIR`（默认 `/data`）下 `danmutv.db`；弹幕/字幕写回视频同目录。
