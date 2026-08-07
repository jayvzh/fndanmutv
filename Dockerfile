# ---- Stage 1: 前端构建 ----
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: 后端运行 ----
FROM python:3.12-slim

# ffmpeg / ffprobe（视频时长、分辨率、内嵌字幕提取）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# 前端构建产物
COPY --from=frontend /app/dist ./static

ENV DANMUTV_DATA_DIR=/data \
    FRONTEND_DIST=/app/static \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# 单 worker：APScheduler 后台任务不能多进程重复触发
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
