#!/bin/bash
# start-frontend.sh - 启动前端开发服务器（避免 TTY 挂起）
#
# 使用方法:
#   ./scripts/start-frontend.sh
#   ./scripts/start-frontend.sh --background  # 后台运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")/frontend"

cd "$FRONTEND_DIR"

if [[ "$1" == "--background" ]]; then
    echo "Starting frontend in background..."
    nohup npm run dev </dev/null > /tmp/frontend.log 2>&1 &
    PID=$!
    echo "Frontend started with PID: $PID"
    echo "Logs: /tmp/frontend.log"
    sleep 3
    if kill -0 $PID 2>/dev/null; then
        echo "✅ Frontend running at http://localhost:5173"
    else
        echo "❌ Frontend failed to start. Check /tmp/frontend.log"
        exit 1
    fi
else
    # 前台运行（交互模式）
    exec npm run dev
fi
