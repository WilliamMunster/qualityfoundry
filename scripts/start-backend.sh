#!/bin/bash
# start-backend.sh - 启动后端开发服务器
#
# 使用方法:
#   ./scripts/start-backend.sh
#   ./scripts/start-backend.sh --background  # 后台运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")/backend"

cd "$BACKEND_DIR"

# 激活虚拟环境
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
fi

if [[ "$1" == "--background" ]]; then
    echo "Starting backend in background..."
    nohup uvicorn qualityfoundry.main:app --reload --port 8000 </dev/null > /tmp/backend.log 2>&1 &
    PID=$!
    echo "Backend started with PID: $PID"
    echo "Logs: /tmp/backend.log"
    sleep 3
    if kill -0 $PID 2>/dev/null; then
        echo "✅ Backend running at http://localhost:8000"
    else
        echo "❌ Backend failed to start. Check /tmp/backend.log"
        exit 1
    fi
else
    # 前台运行（交互模式）
    exec uvicorn qualityfoundry.main:app --reload --port 8000
fi
