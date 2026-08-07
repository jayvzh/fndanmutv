#!/usr/bin/env bash
# DanmuTV 开发环境启动脚本。
# 用法: ./dev.sh [all|backend|frontend]
#   all(默认): 同时启动后端(8000, 带 reload)与前端(5173)
#   backend   : 仅启动后端
#   frontend  : 仅启动前端
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-all}"

start_backend() {
  cd "$ROOT/backend"
  exec conda run --no-capture-output -n danmu \
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

start_frontend() {
  cd "$ROOT/frontend"
  exec npm run dev
}

case "$TARGET" in
  backend)
    start_backend
    ;;
  frontend)
    start_frontend
    ;;
  all)
    start_backend &
    BPID=$!
    start_frontend &
    FPID=$!
    trap 'kill $BPID $FPID 2>/dev/null || true' EXIT INT TERM
    wait -n $BPID $FPID || true
    ;;
  *)
    echo "用法: $0 [all|backend|frontend]" >&2
    exit 1
    ;;
esac
