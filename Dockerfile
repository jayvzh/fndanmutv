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

# ---- Stage 2: 后端运行 ----
FROM python:3.12-slim

# ffmpeg / ffprobe（视频时长、分辨率、内嵌字幕提取）
# 清空代理 + 换国内 Debian 源（python:3.12-slim 基于 Debian trixie）
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY= \
    && (sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
        || sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null \
        || true) \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip 用国内源
COPY backend/requirements.txt ./
RUN export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= all_proxy= ALL_PROXY= no_proxy= NO_PROXY= \
    && pip install --no-cache-dir --timeout 120 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY backend/ ./

# 前端构建产物
COPY --from=frontend /app/dist ./static

# 默认配置：开箱即用（不修改也能直接运行）
ENV DANMUTV_DATA_DIR=/data \
    DANMUTV_FRONTEND_DIST=/app/static \
    DANMUTV_TOKEN=fn-danmutv \
    DANMUTV_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# 单 worker：APScheduler 后台任务不能多进程重复触发
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
