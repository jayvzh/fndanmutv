# FnDanmuTV 弹幕刮削影视版(Docker)

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

内置 fndanmutv + danmu-api，一条命令拉起：

```bash
services:
  fndanmutv:
    build: .
    image: jayvzh/fndanmutv:latest
    container_name: fndanmutv
    restart: unless-stopped
    ports:
      - "8017:8017"
    environment:
      - DANMUTV_TOKEN=fndanmutv
      - DANMUTV_LOG_LEVEL=INFO
      - TZ=Asia/Shanghai
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
    container_name: fndanmutv-danmu-api
    restart: unless-stopped
    ports:
      - "9321:9321"
    volumes:
      - ./danmu-api-data:/data
```

浏览器打开 `http://<host>:8017`，默认 Token：`fndanmutv`（建议通过环境变量 `DANMUTV_TOKEN` 修改）。

### 独立版

仅启动 FnDanmuTV，需自行提供 danmu-api：

```bash
services:
  fndanmutv:
    build: .
    image: jayvzh/fndanmutv:latest
    container_name: fndanmutv
    restart: unless-stopped
    network_mode: host
    environment:
      - DANMUTV_TOKEN=fndanmutv
      - DANMUTV_LOG_LEVEL=INFO
      - TZ=Asia/Shanghai
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

## 项目文档

| 文档 | 内容 |
| --- | --- |
| [开发规则.md](开发规则.md) | 开发第一份规则：文档地图、铁律、常用命令、交付自检 |
| [docs/PRD.md](docs/PRD.md) | 产品需求：背景、使用场景、功能需求、非目标与业务规则 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 技术架构：分层、鉴权、刮削状态机、限流重试与定时任务 |
| [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) | 目录结构、模块职责、核心数据流 |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | SQLite 表结构、迁移约定、全部配置项 |
| [docs/API.md](docs/API.md) | HTTP API 契约（前后端必读，唯一契约来源） |
| [docs/UI_DESIGN.md](docs/UI_DESIGN.md) | 页面布局与交互设计 |
| [docs/DEVELOPMENT_RULES.md](docs/DEVELOPMENT_RULES.md) | 开发完整总则与模块边界约束（永久生效） |
| [docs/context.md](docs/context.md) | 项目背景与现状 |
| [docs/decisions.md](docs/decisions.md) | 重要技术选型决策记录（ADR） |
| [docs/pitfalls.md](docs/pitfalls.md) | 非显而易见的坑与绕开姿势 |
| [docs/conventions.md](docs/conventions.md) | 项目专属约定、命名缩写与技术债 |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | 本地开发、ffmpeg 构建与部署细节 |

## 致谢

基于原 MoviePilot 插件作者 jayvzh 的 DanmuTV 及 HankunYu 的原插件改造，弹幕数据由 danmu-api 提供。
