# Fn-DanmuTV 弹幕刮削

从弹幕 API 后端（[danmu-api](https://github.com/huangxd-/danmu_api)，弹弹 play 兼容协议）获取影视弹幕，转换为 ASS 弹幕字幕并可与原有字幕合并。由原 MoviePilot V2 插件剥离而来，**不依赖 MoviePilot**，以单 Docker 容器提供 Web UI 与 API。

## 功能特性

- 电视剧 / 电影 / 动漫等多类型媒体，按文件名匹配弹幕
- 单文件 / 目录批量刮削，后台串行、全局限流退避（防 429）
- 失败重试：指数退避 `[5,30,60,120,240,480]` 分钟，最多 10 次
- 手动匹配作品 + 集数偏移（写入媒体目录 `.dandan.anime.json`）
- 弹幕参数可调，支持保存 / 切换预设方案（字号、透明度、持续时间、屏幕区域、多层弹幕、随机顶/底、密度、宽度扩展）
- 内嵌字幕提取与合并（`.withDanmu.ass`），支持 `.strm`
- 媒体库自动刮削：可按间隔定时扫描，支持增量 / 完整扫描；默认关闭，仅手动刮削
- 仪表盘 / 目录浏览 / 重试任务 / 历史记录 / 残留字幕清理，刮削完成全局通知

## 快速开始（Docker Compose，首选）

提供两个 compose 文件，使用**同一个镜像**，区别仅在于是否内置 danmu-api：

| 文件                              | 内置 danmu-api | 适用场景              |
| ------------------------------- | ------------ | ----------------- |
| `docker-compose.yml`            | 是            | 一键部署，无需额外准备弹幕 API |
| `docker-compose.standalone.yml` | 否            | 你已有外部弹幕 API       |

### 完整版（推荐）

内置 fn-danmutv + danmu-api，一条命令拉起：

```bash
services:
  danmutv:
    build: .
    image: jayvzh/fn-danmutv:latest
    container_name: fn-danmutv
    restart: unless-stopped
    ports:
      - "8017:8017"
    environment:
      - DANMUTV_TOKEN=fn-danmutv
      - DANMUTV_LOG_LEVEL=INFO
      - DANMUTV_PORT=8017
      - DANMUTV_DANMU_API_URL=http://danmu-api:9321
    volumes:
      - ./data:/data
      # 媒体库，必须可写（弹幕/合并字幕写回视频同目录）
      - ./media:/media:rw
    depends_on:
      - danmu-api
  # 弹幕 API 后端（弹弹 play 兼容）
  danmu-api:
    image: ghcr.io/huangxd-/danmu_api:latest
    container_name: fn-danmu-api
    restart: unless-stopped
    ports:
      - "9321:9321"
    volumes:
      - ./danmu-api-data:/data
```

浏览器打开 `http://<host>:8017`，默认 Token：`fn-danmutv`（建议通过环境变量 `DANMUTV_TOKEN` 修改）。

### 独立版

仅启动 DanmuTV，需自行提供 danmu-api：

```bash
services:
  danmutv:
    build: .
    image: jayvzh/fn-danmutv:latest
    container_name: fn-danmutv
    restart: unless-stopped
    network_mode: host
    environment:
      - DANMUTV_TOKEN=fn-danmutv
      - DANMUTV_LOG_LEVEL=INFO
      - DANMUTV_PORT=8017
      - DANMUTV_DANMU_API_URL=http://127.0.0.1:9321
    volumes:
      - ./data:/data
      # 媒体库，必须可写：
      - ./media:/media:rw
```

使用 host 网络模式，容器直接监听宿主机 `8017`（由 `DANMUTV_PORT` 控制），且 `127.0.0.1` 即宿主机，可直接访问宿主机上运行的 `http://127.0.0.1:9321`。host 模式下无需 `ports` 映射。若 danmu-api 在其他主机，修改 compose 中的 `DANMUTV_DANMU_API_URL`。

> **挂载须知**
>
> - 媒体卷必须以 `:rw` 挂载，弹幕 / 合并字幕会写回视频文件所在目录。
> - 容器内路径与 Web UI 中显示 / 配置的路径必须一致（如 `/media/电影/xxx.mkv`）。

### 本地构建镜像

镜像内的 `ffmpeg` / `ffprobe` 为静态二进制（GPLv3，来自 johnvansickle，由 eugeneware/ffmpeg-static 打包），**不随 git 仓库分发**，需在构建前手动下载到 `references/ffmpeg/` 目录。文件缺失时 `docker build` 会在 `COPY` 步骤直接报错。

下载 `b6.1.1`（ffmpeg 7.0.2）对应你要构建的架构（多架构构建请下载全部四个）：

```bash
mkdir -p references/ffmpeg && cd references/ffmpeg
BASE=https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1
curl -fL -O $BASE/ffmpeg-linux-x64.gz   -O $BASE/ffprobe-linux-x64.gz \
         -O $BASE/ffmpeg-linux-arm64.gz -O $BASE/ffprobe-linux-arm64.gz
```

校验 sha256：

```bash
sha256sum -c - <<'EOF'
bfe8a8fc511530457b528c48d77b5737527b504a3797a9bc4866aeca69c2dffa  ffmpeg-linux-x64.gz
25d9b6ccb05e3d9de9e04e31e2506d8dd7f9f0418981965ac6df12e8d3afd067  ffprobe-linux-x64.gz
754a678672298bc68156adff58aa7385a592c2b30b1d0ae8750c45c915c4bac0  ffmpeg-linux-arm64.gz
2ab6aba60ee84412dff9188720703376cb4e7aaf7e0b5e43aa8249f2acae5bf8  ffprobe-linux-arm64.gz
EOF
```

随后构建：

```bash
# 单架构
docker build -t jayvzh/fn-danmutv:latest .

# 多架构（amd64 + arm64）并推送到 registry
docker buildx build --platform linux/amd64,linux/arm64 \
  -t jayvzh/fn-danmutv:latest --push .

# 或直接用 compose 构建本地单架构镜像
docker compose up -d --build      # 完整版
# docker compose -f docker-compose.standalone.yml up -d --build
```

## 配置

所有环境变量都有默认值，不修改也能直接运行。

| 变量                      | 默认值                     | 说明                                   |
| ----------------------- | ----------------------- | ------------------------------------ |
| `DANMUTV_TOKEN`         | （无内置）              | API / Web 访问 Token；镜像不内置任何凭证，未设置时后端自动生成随机 Token 并打印到启动日志 |
| `DANMUTV_PORT`          | `8017`                  | 容器内监听端口（uvicorn `--port`）             |
| `DANMUTV_DATA_DIR`      | `/data`                 | SQLite 数据库与数据目录                      |
| `DANMUTV_LOG_LEVEL`     | `INFO`                  | 日志级别（DEBUG/INFO/WARNING/ERROR）       |
| `DANMUTV_DANMU_API_URL` | `http://danmu-api:9321` | 弹幕 API 地址，首次启动写入数据库，之后以 Web UI「配置」为准 |
| `DANMUTV_FRONTEND_DIST` | `/app/static`           | 前端构建产物目录（容器内）                        |

> 兼容：也可用 `ADMIN_TOKEN` 作为 Token 变量名（优先级高于 `DANMUTV_TOKEN`）。
>
> 两个 compose 的默认 API 地址不同：完整版指向内置容器 `http://danmu-api:9321`；独立版（host 网络）指向宿主机 `http://127.0.0.1:9321`。

### 端口与卷

| 项                  | 值                     | 说明              |
| ------------------ | --------------------- | --------------- |
| Web 端口             | `8017`（完整版 `8017:8017`；独立版 host 模式直接监听宿主 8017） | 浏览器访问，可用 `DANMUTV_PORT` 改容器端口 |
| danmu-api 端口       | `9321`                | 仅完整版暴露          |
| `./data`           | `/data`               | SQLite 数据库（持久化） |
| `./media`          | `/media`              | 媒体库（必须可写）       |
| `./danmu-api-data` | `/data`（danmu-api 容器） | 仅完整版，弹幕 API 缓存  |

## 本地开发

后端 conda 环境 `danmu`（Python 3.12），前端 Node 18+，本机需安装 `ffmpeg` / `ffprobe`。根目录 `dev.sh` 一键管理：

```bash
./dev.sh start      # 后端 :8021 + 前端 :8017（前端已代理 /api 到后端）
./dev.sh status     # 查看状态
./dev.sh logs       # 查看日志
./dev.sh stop       # 停止全部
```

- 前端 <http://localhost:8017> ，后端 <http://localhost:8021> ，健康检查 <http://localhost:8021/health>
- 本地开发 Token 固定为 `dev-token`（见 `backend/.env`）

## 目录结构

```
backend/                       FastAPI 后端
frontend/                      Vue 3 + Vuetify 3 SPA
references/ffmpeg/             静态 ffmpeg/ffprobe（amd64/arm64，不入库，构建前下载，构建时打入镜像）
Dockerfile                     多阶段构建（Node 构建前端 + python:3.12-slim + 静态 ffmpeg）
docker-compose.yml             完整版（内置 danmu-api）
docker-compose.standalone.yml  独立版（仅 DanmuTV，需外部 API）
dev.sh                         本地开发环境管理脚本
```

## 致谢

基于原 MoviePilot 插件作者 jayvzh 的 DanmuTV 及 HankunYu 的原插件改造，弹幕数据由 danmu-api / 弹弹 play 提供。
