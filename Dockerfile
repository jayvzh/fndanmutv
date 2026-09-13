# ---- Stage 1: 前端构建 ----
FROM node:20-alpine AS frontend
WORKDIR /app
# 显式清空代理（BuildKit 可能从宿主机注入不可达的 127.0.0.1 代理），使用国内 npm 源
COPY frontend/package.json frontend/package-lock.json* ./
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY= \
    && npm config set registry https://registry.npmmirror.com \
    && npm install
COPY frontend/ ./
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY= \
    && npm run build

# ---- Stage 2: 解压静态 ffmpeg/ffprobe（自包含，无 Mesa/LLVM 等图形依赖） ----
# 来源：eugeneware/ffmpeg-static b6.1.1（基于 johnvansickle 静态构建，GPL，ffmpeg 7.0.2）
# 二进制不入库，构建前下载到 references/ffmpeg/（见 README），按 TARGETARCH 选择 x64/arm64
FROM alpine:3.20 AS ffmpeg
ARG TARGETARCH
WORKDIR /out
# 静态 ffmpeg/ffprobe 二进制不入库；构建前需按 README 指引下载到 references/ffmpeg/。
# 文件缺失时此处 COPY 会直接报错终止。
COPY references/ffmpeg/ffmpeg-linux-x64.gz references/ffmpeg/ffprobe-linux-x64.gz \
     references/ffmpeg/ffmpeg-linux-arm64.gz references/ffmpeg/ffprobe-linux-arm64.gz /tmp/
# UPX 压缩：两个静态二进制 153MB → 约 45MB（运行时自解压，字幕提取为低频操作）
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY=; \
    set -eux; \
    sed -i 's|dl-cdn.alpinelinux.org|mirrors.aliyun.com|g' /etc/apk/repositories; \
    apk add --no-cache upx; \
    case "${TARGETARCH}" in \
        amd64) SUFFIX=x64 ;; \
        arm64) SUFFIX=arm64 ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    gunzip /tmp/ffmpeg-linux-${SUFFIX}.gz /tmp/ffprobe-linux-${SUFFIX}.gz; \
    install -m 0755 /tmp/ffmpeg-linux-${SUFFIX} /out/ffmpeg; \
    install -m 0755 /tmp/ffprobe-linux-${SUFFIX} /out/ffprobe; \
    rm -f /tmp/ffmpeg-*.gz /tmp/ffprobe-*.gz; \
    upx -9 --lzma /out/ffmpeg /out/ffprobe; \
    /out/ffmpeg -version | head -1; \
    /out/ffprobe -version | head -1

# ---- Stage 3: 后端运行 ----
FROM python:3.12-slim

# tzdata / ca-certificates 在 python:3.12-slim 中已内置：
# tzdata 供 zoneinfo 解析 TZ（代码默认东八区，见 app/timeutil.py），ca-certificates 供 requests 访问 HTTPS。
# ffmpeg 走 UPX 压缩的静态二进制（见 Stage 2），无需 apt 安装。

WORKDIR /app

# pip 用国内源；装完即卸载 pip 自身（约 -12MB），并清理 __pycache__/测试目录瘦身
COPY backend/requirements.txt ./
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY= \
    && pip install --no-cache-dir --timeout 120 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
    && pip uninstall -y pip \
    && find /usr/local/lib/python3.12 -depth -type d \( -name '__pycache__' -o -name 'tests' -o -name 'test' \) -exec rm -rf {} +

COPY backend/ ./

# 前端构建产物
COPY --from=frontend /app/dist ./static

# 静态 ffmpeg / ffprobe
COPY --from=ffmpeg /out/ffmpeg /out/ffprobe /usr/local/bin/

# 默认配置：开箱即用（不修改也能直接运行）
# Token 不在镜像中内置，运行时通过 DANMUTV_TOKEN/ADMIN_TOKEN 注入；
# 未设置时后端自动生成随机 Token 并打印到日志（见 app/config.py）
# 容器内监听端口可通过 DANMUTV_PORT 覆盖（默认 8017）
ENV DANMUTV_DATA_DIR=/data \
    DANMUTV_MEDIA_DIR=/media \
    DANMUTV_FRONTEND_DIST=/app/static \
    DANMUTV_LOG_LEVEL=INFO \
    DANMUTV_PORT=8017 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

VOLUME ["/data"]
EXPOSE 8017

# 用 Python 标准库做健康检查，无需安装 curl；端口读取 DANMUTV_PORT
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('DANMUTV_PORT','8017'), timeout=5).status == 200 else 1)"

# 单 worker：APScheduler 后台任务不能多进程重复触发
# 用 sh -c 展开 DANMUTV_PORT，exec 让 uvicorn 接管 PID 1 以正常接收信号
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${DANMUTV_PORT}"]
