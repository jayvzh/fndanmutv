# Fn-DanmuTV 弹幕刮削 开发说明

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
