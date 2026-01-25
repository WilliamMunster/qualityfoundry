#!/bin/bash
# start-all.sh - 启动前后端服务
#
# 使用方法:
#   ./scripts/start-all.sh           # 后台启动全部
#   ./scripts/start-all.sh --stop    # 停止全部

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$1" == "--stop" ]]; then
    echo "Stopping services..."
    pkill -f "uvicorn qualityfoundry" 2>/dev/null && echo "Backend stopped" || echo "Backend not running"
    pkill -f "vite" 2>/dev/null && echo "Frontend stopped" || echo "Frontend not running"
    exit 0
fi

echo "Starting QualityFoundry services..."
echo ""

# Start backend
"$SCRIPT_DIR/start-backend.sh" --background

# Start frontend
"$SCRIPT_DIR/start-frontend.sh" --background

echo ""
echo "============================================"
echo "✅ All services started"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "============================================"
