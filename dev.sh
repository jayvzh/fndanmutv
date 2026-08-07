#!/usr/bin/env bash
# DanmuTV 开发环境启动脚本
# 用法: ./dev.sh {start|stop|restart|status|logs} [backend|frontend]
set -euo pipefail

# ── 路径 ──
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"

# ── 初始化（日志目录和 PID 目录自动创建）──
mkdir -p "$LOG_DIR" "$PID_DIR"

# ── 加载环境 ──
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

CONDA_BASE="$HOME/miniconda3"
__conda_setup="$("$CONDA_BASE/bin/conda" 'shell.bash' 'hook' 2>/dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    export PATH="$CONDA_BASE/bin:$PATH"
fi

# ── 颜色 ──
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── 配置 ──
BACKEND_PORT=8021
FRONTEND_PORT=8017
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
CONDA_ENV="danmu"

# ── 检查端口占用 ──
check_port() {
    local port=$1
    if command -v ss &>/dev/null; then
        ss -tlnp 2>/dev/null | grep -q ":$port " && return 0
    elif command -v lsof &>/dev/null; then
        lsof -i :$port -t &>/dev/null && return 0
    fi
    return 1
}

# ── 获取占用端口的 PID ──
port_pids() {
    local port=$1
    if command -v ss &>/dev/null; then
        ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | sort -u
    elif command -v lsof &>/dev/null; then
        lsof -i :$port -t 2>/dev/null | sort -u
    fi
}

# ── 获取 PID 状态 ──
get_pid() {
    local pid_file=$1
    [ -f "$pid_file" ] && cat "$pid_file" 2>/dev/null || echo ""
}

is_running() {
    local pid=$1
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

# ── 需要 conda 环境的命令才激活 ──
ensure_conda() {
    conda activate "$CONDA_ENV" 2>/dev/null || {
        error "无法激活 conda 环境 '$CONDA_ENV'，请先运行: conda create -n $CONDA_ENV python=3.12"
        return 1
    }
}

# ── 强制清理端口占用 ──
kill_port() {
    local name=$1
    local port=$2
    local pids=$(port_pids $port)

    if [ -z "$pids" ]; then
        info "$name 端口 $port 无占用"
        return 0
    fi

    warn "$name 端口 $port 被 PID $(echo $pids | tr '\n' ' ')占用，强制清理..."
    for pid in $pids; do
        kill "$pid" 2>/dev/null || true
    done
    sleep 1
    for pid in $pids; do
        is_running "$pid" && kill -9 "$pid" 2>/dev/null || true
    done
    info "$name 端口 $port 已清理"
}

# ── 处理端口占用：空闲放行；占用时交互询问清理 ──
# 返回 0 = 可继续启动，1 = 中止
handle_port_conflict() {
    local name=$1
    local port=$2
    local pid_file=$3

    if ! check_port "$port"; then
        return 0
    fi

    # 端口被占用，交互询问
    warn "$name 端口 $port 已被占用"
    if [ ! -t 0 ]; then
        error "非交互模式无法询问，请用 ./dev.sh restart 强制清理后启动"
        return 1
    fi
    local answer=""
    read -rp "是否清理占用进程并继续启动？[Y/n] " answer || true
    case "$answer" in
        [Nn]*)
            warn "已取消，跳过 $name 启动"
            return 1
            ;;
        *)
            kill_port "$name" "$port"
            rm -f "$pid_file"
            ;;
    esac

    # 再次确认端口已释放
    if check_port "$port"; then
        error "$name 端口 $port 仍被占用，无法启动"
        return 1
    fi
    return 0
}

# ── 启动后端 ──
start_backend() {
    ensure_conda || return 1

    local pid=$(get_pid "$BACKEND_PID_FILE")
    if is_running "$pid"; then
        warn "后端已在运行 (PID: $pid)"
        return 0
    fi

    handle_port_conflict "后端" $BACKEND_PORT "$BACKEND_PID_FILE" || return 1

    info "启动后端 (FastAPI :$BACKEND_PORT)..."
    cd "$BACKEND_DIR"
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT \
        > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    cd "$PROJECT_ROOT"

    sleep 2
    pid=$(get_pid "$BACKEND_PID_FILE")
    if is_running "$pid"; then
        info "后端已启动 (PID: $pid) -> http://localhost:$BACKEND_PORT"
        info "日志: $BACKEND_LOG"
    else
        error "后端启动失败，查看日志: $BACKEND_LOG"
        tail -20 "$BACKEND_LOG" 2>/dev/null
        return 1
    fi
}

# ── 启动前端 ──
start_frontend() {
    local pid=$(get_pid "$FRONTEND_PID_FILE")
    if is_running "$pid"; then
        warn "前端已在运行 (PID: $pid)"
        return 0
    fi

    handle_port_conflict "前端" $FRONTEND_PORT "$FRONTEND_PID_FILE" || return 1

    info "启动前端 (Vite :$FRONTEND_PORT)..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    cd "$PROJECT_ROOT"

    sleep 2
    pid=$(get_pid "$FRONTEND_PID_FILE")
    if is_running "$pid"; then
        info "前端已启动 (PID: $pid) -> http://localhost:$FRONTEND_PORT"
        info "日志: $FRONTEND_LOG"
    else
        error "前端启动失败，查看日志: $FRONTEND_LOG"
        tail -20 "$FRONTEND_LOG" 2>/dev/null
        return 1
    fi
}

# ── 停止进程（优雅退出）──
stop_process() {
    local name=$1
    local pid_file=$2
    local pid=$(get_pid "$pid_file")

    if [ -z "$pid" ]; then
        return 0
    fi

    if is_running "$pid"; then
        info "停止 $name (PID: $pid)..."
        kill "$pid" 2>/dev/null
        for i in $(seq 1 10); do
            is_running "$pid" || break
            sleep 0.5
        done
        if is_running "$pid"; then
            warn "$name 未响应 SIGTERM，发送 SIGKILL..."
            kill -9 "$pid" 2>/dev/null
            sleep 1
        fi
        info "$name 已停止"
    fi
    rm -f "$pid_file"
}

# ── 命令 ──
cmd_start() {
    info "=== DanmuTV 开发环境启动 ==="
    start_backend || warn "后端未就绪，继续启动前端"
    start_frontend || warn "前端未就绪"
    echo ""
    info "启动完成:"
    echo -e "  ${CYAN}前端${NC}: http://localhost:$FRONTEND_PORT"
    echo -e "  ${CYAN}后端${NC}: http://localhost:$BACKEND_PORT"
    echo -e "  ${CYAN}健康检查${NC}: http://localhost:$BACKEND_PORT/health"
    echo ""
    echo "查看日志: ./dev.sh logs"
    echo "停止服务: ./dev.sh stop"
}

cmd_stop() {
    info "=== 停止 DanmuTV 开发环境 ==="
    stop_process "前端" "$FRONTEND_PID_FILE"
    stop_process "后端" "$BACKEND_PID_FILE"
    info "已全部停止"
}

cmd_restart() {
    info "=== 重启 DanmuTV 开发环境 ==="
    # 强制清理端口（跳过确认）
    kill_port "前端" $FRONTEND_PORT; rm -f "$FRONTEND_PID_FILE"
    kill_port "后端" $BACKEND_PORT; rm -f "$BACKEND_PID_FILE"
    sleep 1
    start_backend || warn "后端未就绪，继续启动前端"
    start_frontend || warn "前端未就绪"
    info "重启完成"
}

cmd_status() {
    echo -e "${CYAN}=== DanmuTV 服务状态 ===${NC}"
    echo ""

    local bpid=$(get_pid "$BACKEND_PID_FILE")
    if is_running "$bpid"; then
        echo -e "  后端: ${GREEN}运行中${NC} (PID: $bpid) -> http://localhost:$BACKEND_PORT"
    else
        echo -e "  后端: ${RED}已停止${NC}"
    fi

    local fpid=$(get_pid "$FRONTEND_PID_FILE")
    if is_running "$fpid"; then
        echo -e "  前端: ${GREEN}运行中${NC} (PID: $fpid) -> http://localhost:$FRONTEND_PORT"
    else
        echo -e "  前端: ${RED}已停止${NC}"
    fi
    echo ""
}

cmd_logs() {
    local target=${1:-all}
    case "$target" in
        backend|b)
            info "后端日志 (Ctrl+C 退出):"
            tail -f "$BACKEND_LOG"
            ;;
        frontend|f)
            info "前端日志 (Ctrl+C 退出):"
            tail -f "$FRONTEND_LOG"
            ;;
        *)
            info "合并日志 (Ctrl+C 退出):"
            tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
            ;;
    esac
}

# ── 入口 ──
case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    cmd_logs "${2:-all}" ;;
    *)
        echo "DanmuTV 开发环境管理脚本"
        echo ""
        echo "用法: ./dev.sh <命令> [backend|frontend]"
        echo ""
        echo "命令:"
        echo "  start              启动前后端（如遇端口占用，提示确认后清理并启动）"
        echo "  stop               停止全部服务"
        echo "  restart            强制清理占用端口后重启全部（跳过确认）"
        echo "  status             查看服务运行状态"
        echo "  logs [backend]     查看日志（默认合并，可指定 backend/frontend）"
        echo ""
        echo "示例:"
        echo "  ./dev.sh start              # 启动前后端"
        echo "  ./dev.sh stop               # 停止全部"
        echo "  ./dev.sh restart            # 强制清理端口后重启"
        echo "  ./dev.sh status             # 查看状态"
        echo "  ./dev.sh logs               # 查看合并日志"
        echo "  ./dev.sh logs backend       # 仅后端日志"
        echo ""
        echo "端口:"
        echo "  后端: $BACKEND_PORT (FastAPI + uvicorn --reload，conda 环境 $CONDA_ENV)"
        echo "  前端: $FRONTEND_PORT (Vite dev server)"
        ;;
esac
