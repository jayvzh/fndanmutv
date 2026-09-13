# 技术决策记录（decisions）

> 只记录重要、非显而易见、未来可能复用的技术选型及其原因。
> 更新时机：做出重要技术选型或方案变更时。格式：日期/标题/背景/决策/原因/影响。

## 模板
- 日期：YYYY-MM-DD
- 标题：
- 背景：
- 决策：
- 原因：
- 影响：

## 2026-09-13 镜像瘦身：ffmpeg UPX 压缩 + 去冗余依赖/系统层
- 背景：镜像逻辑体积 448MB（`docker inspect`），其中静态 ffmpeg/ffprobe 合计 153MB、site-packages 48MB；`python:3.12-slim` 基础层约 190MB。
- 决策：
  1. ffmpeg stage 用 Alpine 包 `upx -9 --lzma` 压缩两个静态二进制（153MB→41MB）；
  2. `uvicorn[standard]` 改为 `uvicorn`（代码不用 uvloop/watchfiles/websockets，site-packages 48MB→18MB）；
  3. 删除 apt 安装层——`python:3.12-slim` 已内置 tzdata（含 zoneinfo 数据）与 ca-certificates；
  4. pip 安装后清理 `__pycache__/tests/test` 目录。
- 原因：ffmpeg/ffprobe 均为低频调用（读取时长/分辨率、字幕提取），UPX 自解压开销可接受；纯 HTTP 服务用 asyncio 默认事件循环即可。
- 影响：镜像 448MB→284MB（优于预期 320MB）。已验证 UPX 压缩后的 ffmpeg 可正常转码、ffprobe JSON 正常、后端 401/200/health/前端页正常。注意：docker hub 拉取为压缩传输（content 93.8MB），本地 `docker images` 显示的是解包后与基础层去重的占用，均非逻辑体积。
- arm64 验证（2026-09-13，QEMU 模拟）：`docker buildx build --platform linux/arm64 --provenance=false --load`，逻辑体积 312MB（amd64 298MB，差异为各架构二进制/字节码体积）。冒烟通过：aarch64、UPX 压缩 ffmpeg libx264 转码与 ffprobe JSON 正常、401/200/前端页/APScheduler 正常。
  - 坑 1：本机启用 containerd image store 时，跨架构 `--load` 后未运行的镜像只显示 content size（arm64 曾显示 87.5MB），运行一次解包后即显示逻辑体积，勿误判为镜像不完整。
  - 坑 2：QEMU 下 `import app.main` 冷启动约 104s，远超 HEALTHCHECK 的 `--start-period=10s --timeout=5s`，容器会残留 unhealthy；真实 arm64 硬件无此问题，无需为模拟环境放宽健康检查参数。
  - 构建网络：dockerd 走 systemd 代理须指向主机可达地址（`socks5h://127.0.0.1:1080` 在 daemon 网络命名空间内不可达）；build-arg 代理只对 RUN 指令生效，拉基础镜像层由 daemon 代理决定；第三方 registry-mirrors 拉 arm64 manifest 可能极慢，必要时移除走代理直连。
