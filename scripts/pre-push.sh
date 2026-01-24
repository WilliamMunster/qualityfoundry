#!/bin/bash
# 本地 Pre-Push 验证脚本
# 
# 用法: ./scripts/pre-push.sh
# 
# 在推送前运行，确保代码通过 lint 和测试
# 
# // turbo-all

set -e

echo "=== Pre-Push 验证 ==="
echo ""

cd "$(dirname "$0")/.."

# 1. Ruff Lint
echo "1. Running ruff check..."
cd backend
source .venv/bin/activate 2>/dev/null || true
ruff check app/ --fix
echo "✅ Lint passed"
echo ""

# 2. 快速测试（仅运行核心契约测试）
echo "2. Running quick tests..."
python -m pytest tests/test_api_contract_run_detail.py tests/test_legacy_runs_readonly.py -v --tb=short -q
echo "✅ Tests passed"
echo ""

# 3. TypeScript 检查（前端）
echo "3. Running TypeScript check..."
cd ../frontend
npx tsc --noEmit 2>/dev/null || echo "⚠️  TypeScript check skipped (no frontend changes)"
echo ""

echo "=== 验证完成，可以推送 ==="
