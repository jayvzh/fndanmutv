# DanmuTV 弹幕刮削（独立版）

从弹幕 API 后端（[danmu-api](https://github.com/huangxd-/danmu_api)，弹弹 play 兼容协议）获取影视弹幕数据，转换为 ASS 弹幕字幕，并可与原有字幕合并。本项目由原 MoviePilot V2 插件剥离而来，**不依赖 MoviePilot**，以单 Docker 容器提供 Web UI 与 API。

## 功能特性

- 电视剧 / 电影 / 动漫等多类型媒体，通过文件名匹配弹幕
- 单文件 / 目录批量刮削，后台串行、全局限流退避（防 429）
- 失败重试：指数退避 `[5,30,60,120,240,480]` 分钟，最多 10 次
- 手动匹配作品 + 集数偏移（写入媒体目录 `.dandan.anime.json`）
- 弹幕参数可调：字号、透明度、持续时间、屏幕区域（全屏/半屏/1/3/1/4）、多层弹幕（2/3 层）、随机顶/底、密度、宽度扩展
- 内嵌字幕提取与合并（`.withDanmu.ass`），支持 `.strm`
- 定时增量扫描媒体库，自动刮削新文件
- 仪表盘 / 目录浏览 / 重试任务 / 历史记录 / 残留字幕清理

## 快速开始

```bash
git clone <repo> && cd fndanmutv
# 编辑 docker-compose.yml，将媒体目录挂载到容器内（如 /media）
docker compose up -d --build
```

浏览器打开 `http://<host>:8000`，输入访问 Token（见下方环境变量）。

### docker-compose.yml 要点

```yaml
services:
  danmutv:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DANMUTV_TOKEN=请修改为你的随机Token
      - DANMUTV_LOG_LEVEL=INFO
    volumes:
      - ./data:/data                 # SQLite 数据库
      - /your/media/path:/media:rw   # 媒体库，必须可写（字幕写回视频同目录）
    depends_on:
      - danmu-api

  danmu-api:                         # 可选；若已有弹幕 API，删除此服务并在配置中指向它
    image: ghcr.io/huangxd-/danmu_api:latest
    ports:
      - "9321:9321"
    volumes:
      - ./danmu-api-data:/data
```

> 媒体卷必须以 `:rw` 挂载，因为弹幕/合并字幕会写回视频文件所在目录。
> 容器内路径与 Web UI 中显示/配置的路径必须一致（即容器内路径，如 `/media/电影/xxx.mkv`）。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DANMUTV_TOKEN` | 启动时随机生成并打印到日志 | API/Web 访问 Token，**强烈建议显式设置** |
| `DANMUTV_DATA_DIR` | `/data` | SQLite 数据库与数据目录 |
| `DANMUTV_LOG_LEVEL` | `INFO` | 日志级别 |
| `FRONTEND_DIST` | `/app/static` | 前端构建产物目录（容器内） |

弹幕 API 地址在 Web UI「配置」中设置，Docker 内网默认为 `http://danmu-api:9321`。

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
- 首次启动若未设置 `DANMUTV_TOKEN`，后端会自动生成临时 Token 并打印到后端日志（`./dev.sh logs backend`）

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
backend/        FastAPI 后端（app/ 含引擎、服务、路由）
frontend/       Vue 3 + Vuetify 3 SPA
data/           运行时数据（SQLite，挂载卷）
Dockerfile      多阶段构建（Node 构建前端 + python:3.12-slim 运行）
```

## 致谢

基于原 MoviePilot 插件作者 jayvzh 的 DanmuTV 及 HankunYu 的原插件改造，弹幕数据由 danmu-api / 弹弹 play 提供。
