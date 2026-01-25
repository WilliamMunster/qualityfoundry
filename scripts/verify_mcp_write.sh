#!/bin/bash
# verify_mcp_write.sh - MCP Write Security 运维验证脚本
# 验证 MCP Server 的安全边界是否正确工作

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")/backend"

echo "=== MCP Write Security Verification ==="
echo ""

# 1. 运行安全测试
echo "1. Running MCP security tests..."
cd "$BACKEND_DIR"
source .venv/bin/activate 2>/dev/null || true

python -m pytest tests/test_mcp_write_security.py tests/test_mcp_server_smoke.py -v --tb=short

echo ""
echo "2. Verifying error codes are defined..."
grep -n "AUTH_REQUIRED\|PERMISSION_DENIED\|POLICY_BLOCKED\|SANDBOX_VIOLATION" \
    app/qualityfoundry/protocol/mcp/errors.py | head -10

echo ""
echo "3. Verifying security chain in server..."
grep -n "_verify_auth\|_check_permission\|_check_policy\|_check_sandbox" \
    app/qualityfoundry/protocol/mcp/server.py | head -10

echo ""
echo "4. Verifying MCP_TOOL_CALL audit event..."
grep -n "MCP_TOOL_CALL" app/qualityfoundry/database/audit_log_models.py

echo ""
echo "=== All MCP Write Security checks passed ==="
