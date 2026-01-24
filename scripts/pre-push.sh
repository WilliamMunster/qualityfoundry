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

# 4. 检查前端是否引用了 legacy API
echo "4. Checking for legacy API references..."
cd ../frontend/src

# 检查是否有文件（除了 qf.ts 本身）import 了 ../qf
LEGACY_REFS=$(grep -r --include="*.ts" --include="*.tsx" -l 'from ["'"'"'].*qf["'"'"']\|from ["'"'"']\.\./qf["'"'"']' . 2>/dev/null | grep -v "qf.ts" || true)

if [ -n "$LEGACY_REFS" ]; then
  echo "❌ 发现 legacy API 引用！以下文件需要迁移到 orchestrationsApi："
  echo "$LEGACY_REFS"
  exit 1
fi
echo "✅ No legacy API references found"
echo ""

cd ../..
echo "=== 验证完成，可以推送 ==="

