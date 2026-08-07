# DanmuTV 弹幕刮削（独立版）

从弹幕 API 后端（[danmu-api](https://github.com/huangxd-/danmu_api)，弹弹 play 兼容协议）获取影视弹幕数据，转换为 ASS 弹幕字幕，并可与原有字幕合并。本项目由原 MoviePilot V2 插件剥离而来，**不依赖 MoviePilot**，以单 Docker 容器提供 Web UI 与 API。

## 功能特性

- 电视剧 / 电影 / 动漫等多类型媒体，通过文件名匹配弹幕
- 单文件 / 目录批量刮削，后台串行、全局限流退避（防 429）
- 失败重试：指数退避 `[5,30,60,120,240,480]` 分钟，最多 10 次
- 手动匹配作品 + 集数偏移（写入媒体目录 `.dandan.anime.json`）
- 弹幕参数可调并支持保存/切换预设方案（字号、透明度、持续时间、屏幕区域、多层弹幕、随机顶/底、密度、宽度扩展）
- 内嵌字幕提取与合并（`.withDanmu.ass`），支持 `.strm`
- 媒体库自动刮削：可按间隔定时扫描，支持「增量扫描（跳过已有弹幕）」与「完整扫描（重新刮削全部）」两种模式；默认关闭，仅手动刮削
- 仪表盘 / 目录浏览 / 重试任务 / 历史记录 / 残留字幕清理
- 刮削完成右下角全局通知，跨页面弹出

## 快速开始

提供两个 compose 文件，使用**同一个镜像**，区别仅在于是否内置 danmu-api 服务：

| 文件 | 包含 danmu-api | 适用场景 |
|---|---|---|
| `docker-compose.yml` | 是 | 一键部署，无需额外准备弹幕 API |
| `docker-compose.standalone.yml` | 否 | 你已有外部弹幕 API |

### 完整版（推荐，内置 danmu-api）

```bash
# 直接使用 Docker Hub 镜像
mkdir -p data media danmu-api-data
curl -O https://raw.githubusercontent.com/jayvzh/fndanmutv/main/docker-compose.yml
docker compose up -d
```

或本地构建：
```bash
docker compose up -d --build
```

浏览器打开 `http://<host>:8017`，默认访问 Token：`fn-danmutv`（建议在环境变量中修改）。

### 独立版（不含 danmu-api）

```bash
curl -O https://raw.githubusercontent.com/jayvzh/fndanmutv/main/docker-compose.standalone.yml
docker compose -f docker-compose.standalone.yml up -d
```

使用 `network_mode: host`，默认访问宿主机上的 `http://127.0.0.1:9321`。如你的 danmu-api 在其他主机，修改 compose 中的 `DANMUTV_DANMU_API_URL`。

> 媒体卷必须以 `:rw` 挂载，因为弹幕/合并字幕会写回视频文件所在目录。
> 容器内路径与 Web UI 中显示/配置的路径必须一致（即容器内路径，如 `/media/电影/xxx.mkv`）。

### 从源码构建并推送到 Docker Hub

```bash
docker build -t jayvzh/fn-danmutv:latest .
docker push jayvzh/fn-danmutv:latest
```

> 只有一个镜像。是否包含 danmu-api 由 compose 文件决定（`docker-compose.yml` 内置，`docker-compose.standalone.yml` 不内置）。

## 环境变量

所有变量都有默认值，**不修改也能直接运行**。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DANMUTV_TOKEN` | `fn-danmutv` | API/Web 访问 Token，生产环境建议修改 |
| `DANMUTV_DATA_DIR` | `/data` | SQLite 数据库与数据目录 |
| `DANMUTV_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `DANMUTV_DANMU_API_URL` | `http://danmu-api:9321`（Dockerfile 默认） | 弹幕 API 地址，首次初始化时写入配置；compose 已按版本设置不同默认值 |
| `DANMUTV_FRONTEND_DIST` | `/app/static` | 前端构建产物目录（容器内） |

> 兼容：也可用 `ADMIN_TOKEN` 作为 Token 变量名（优先级高于 `DANMUTV_TOKEN`）。

弹幕 API 地址首次启动时从环境变量写入数据库，之后以 Web UI「配置」中保存的值为准。两个 compose 文件的默认值：
- **完整版**（`docker-compose.yml`）：`http://danmu-api:9321`（访问内置 danmu-api 容器）
- **独立版**（`docker-compose.standalone.yml`）：`http://127.0.0.1:9321`（使用 host 网络模式访问宿主机上的 danmu-api）

## 端口与卷

| 项 | 值 | 说明 |
|---|---|---|
| Web 端口 | `8017` → 容器 `8000` | 浏览器访问 |
| danmu-api 端口 | `9321` | 仅完整版暴露 |
| `./data` | `/data` | SQLite 数据库（持久化） |
| `./media` | `/media` | 媒体库（必须可写） |
| `./danmu-api-data` | `/data`（danmu-api 容器） | 仅完整版，弹幕 API 缓存 |

## 本地开发

后端使用 conda `danmu` 环境（Python 3.12），前端 Node 18+。推荐用项目根目录的 `dev.sh` 一键启动：

```bash
./dev.sh start      # 启动后端(:8021) + 前端(:8017)，自动激活 conda danmu
./dev.sh status     # 查看状态
./dev.sh logs       # 查看日志（logs/backend.log、logs/frontend.log）
./dev.sh restart    # 强制清理端口后重启
./dev.sh stop       # 停止全部
```

- 前端：http://localhost:8017 （已配置 `/api` 代理到后端 8021）
- 后端 API：http://localhost:8021 ，健康检查 http://localhost:8021/health
- 本地开发 Token 固定为 `dev-token`（见 `backend/.env`）

手动启动方式：

```bash
# 后端
conda activate danmu
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8021

# 前端
cd frontend
npm install
npm run dev   # http://localhost:8017
```

运行需要系统安装 `ffmpeg` / `ffprobe`（用于视频时长、分辨率与内嵌字幕提取）。

## 目录结构

```
backend/             FastAPI 后端（app/ 含引擎、服务、路由）
frontend/            Vue 3 + Vuetify 3 SPA
Dockerfile           多阶段构建（Node 构建前端 + python:3.12-slim 运行，含 ffmpeg）
docker-compose.yml            完整版（内置 danmu-api）
docker-compose.standalone.yml 独立版（仅 DanmuTV，需外部 API）
dev.sh               本地开发环境管理脚本
```

## 致谢

基于原 MoviePilot 插件作者 jayvzh 的 DanmuTV 及 HankunYu 的原插件改造，弹幕数据由 danmu-api / 弹弹 play 提供。
