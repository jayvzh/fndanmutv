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
# 二进制随仓库分发于 docker/ffmpeg/，避免构建时联网
FROM alpine:3.20 AS ffmpeg
WORKDIR /out
COPY docker/ffmpeg/ffmpeg-linux-x64.gz docker/ffmpeg/ffprobe-linux-x64.gz /tmp/
RUN gunzip /tmp/ffmpeg-linux-x64.gz /tmp/ffprobe-linux-x64.gz \
    && install -m 0755 /tmp/ffmpeg-linux-x64 /out/ffmpeg \
    && install -m 0755 /tmp/ffprobe-linux-x64 /out/ffprobe \
    && /out/ffmpeg -version | head -1 \
    && /out/ffprobe -version | head -1

# ---- Stage 3: 后端运行 ----
FROM python:3.12-slim

# 系统层：仅保留时区与证书，ffmpeg 走静态二进制（不再 apt install ffmpeg，避免拉入 libllvm/mesa 等 ~300MB 图形库）
# 清空代理 + 换国内 Debian 源（python:3.12-slim 基于 Debian trixie）
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY= \
    && (sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
        || sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null \
        || true) \
    && apt-get update \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip 用国内源；装完即卸载 pip 自身以瘦身（约 -12MB）
COPY backend/requirements.txt ./
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY= \
    && pip install --no-cache-dir --timeout 120 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
    && pip uninstall -y pip

COPY backend/ ./

# 前端构建产物
COPY --from=frontend /app/dist ./static

# 静态 ffmpeg / ffprobe
COPY --from=ffmpeg /out/ffmpeg /out/ffprobe /usr/local/bin/

# 默认配置：开箱即用（不修改也能直接运行）
ENV DANMUTV_DATA_DIR=/data \
    DANMUTV_FRONTEND_DIST=/app/static \
    DANMUTV_TOKEN=fn-danmutv \
    DANMUTV_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

VOLUME ["/data"]
EXPOSE 8000

# 用 Python 标准库做健康检查，无需安装 curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status == 200 else 1)"

# 单 worker：APScheduler 后台任务不能多进程重复触发
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
