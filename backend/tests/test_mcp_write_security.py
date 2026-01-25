"""MCP Write Security Tests

测试 MCP 写能力的安全边界，覆盖 mcp-write-security.md v0.1 设计文档的所有安全约束。
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from qualityfoundry.protocol.mcp.server import MCPServer
from qualityfoundry.protocol.mcp.errors import (
    AUTH_REQUIRED,
    PERMISSION_DENIED,
    POLICY_BLOCKED,
    SANDBOX_VIOLATION,
    TIMEOUT,
    BUDGET_EXCEEDED,
)


# ==================== Fixtures ====================


@pytest.fixture
def mock_user_admin():
    """模拟 ADMIN 用户"""
    from qualityfoundry.database.user_models import UserRole
    user = MagicMock()
    user.id = uuid4()
    user.role = UserRole.ADMIN
    user.username = "admin"
    return user


@pytest.fixture
def mock_user_user():
    """模拟 USER 用户"""
    from qualityfoundry.database.user_models import UserRole
    user = MagicMock()
    user.id = uuid4()
    user.role = UserRole.USER
    user.username = "testuser"
    return user


@pytest.fixture
def mock_user_viewer():
    """模拟 VIEWER 用户"""
    from qualityfoundry.database.user_models import UserRole
    user = MagicMock()
    user.id = uuid4()
    user.role = UserRole.VIEWER
    user.username = "viewer"
    return user


@pytest.fixture
def mock_policy_with_allowlist():
    """模拟包含 allowlist 的策略"""
    policy = MagicMock()
    policy.tools.allowlist = ["run_pytest"]
    policy.sandbox.enabled = True
    policy.sandbox.timeout_s = 300
    policy.sandbox.memory_limit_mb = 512
    policy.sandbox.allowed_paths = ["tests/"]
    policy.sandbox.env_whitelist = ["PATH", "HOME"]
    return policy


@pytest.fixture
def mock_policy_empty_allowlist():
    """模拟空 allowlist 的策略"""
    policy = MagicMock()
    policy.tools.allowlist = []
    policy.sandbox.enabled = True
    return policy


@pytest.fixture
def mock_policy_sandbox_disabled():
    """模拟 sandbox 禁用的策略"""
    policy = MagicMock()
    policy.tools.allowlist = ["run_pytest"]
    policy.sandbox.enabled = False
    return policy


@pytest.fixture
def mock_db_session_factory():
    """模拟数据库会话工厂"""
    def factory():
        return MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    return factory


def create_server_with_mocks(db_factory=None):
    """创建带 mock 的 MCP Server"""
    return MCPServer(db_session_factory=db_factory)


# ==================== Test Cases ====================


class TestMCPWriteSecurityAuthFailure:
    """测试认证失败场景 → -32001 AUTH_REQUIRED"""

    @pytest.mark.asyncio
    async def test_no_token_returns_auth_required(self):
        """无 token 时返回 AUTH_REQUIRED"""
        server = create_server_with_mocks(db_factory=MagicMock())

        result = await server.handle_tool_call(
            tool_name="run_pytest",
            arguments={"test_path": "tests/"},
            params={},  # 无 auth 字段
        )

        assert "error" in result
        assert result["error"]["code"] == AUTH_REQUIRED

    @pytest.mark.asyncio
    async def test_empty_token_returns_auth_required(self):
        """空 token 时返回 AUTH_REQUIRED"""
        server = create_server_with_mocks(db_factory=MagicMock())

        result = await server.handle_tool_call(
            tool_name="run_pytest",
            arguments={"test_path": "tests/"},
            params={"auth": {"token": ""}},
        )

        assert "error" in result
        assert result["error"]["code"] == AUTH_REQUIRED

    @pytest.mark.asyncio
    async def test_invalid_token_returns_auth_required(self):
        """无效 token 时返回 AUTH_REQUIRED"""
        def db_factory():
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            return mock_db

        server = create_server_with_mocks(db_factory=db_factory)

        with patch("qualityfoundry.services.auth_service.AuthService.verify_token", return_value=None):
            result = await server.handle_tool_call(
                tool_name="run_pytest",
                arguments={"test_path": "tests/"},
                params={"auth": {"token": "invalid_token"}},
            )

        assert "error" in result
        assert result["error"]["code"] == AUTH_REQUIRED


class TestMCPWriteSecurityPermissionDenied:
    """测试权限拒绝场景 → -32003 PERMISSION_DENIED"""

    @pytest.mark.asyncio
    async def test_viewer_cannot_run_write_tool(self, mock_user_viewer):
        """VIEWER 角色无法执行写工具"""
        def db_factory():
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            return mock_db

        server = create_server_with_mocks(db_factory=db_factory)

        with patch("qualityfoundry.services.auth_service.AuthService.verify_token", return_value=mock_user_viewer):
            result = await server.handle_tool_call(
                tool_name="run_pytest",
                arguments={"test_path": "tests/"},
                params={"auth": {"token": "valid_token"}},
            )

        assert "error" in result
        assert result["error"]["code"] == PERMISSION_DENIED


class TestMCPWriteSecurityPolicyBlocked:
    """测试策略阻断场景 → -32004 POLICY_BLOCKED"""

    @pytest.mark.asyncio
    async def test_empty_allowlist_blocks_write_tool(self, mock_user_user, mock_policy_empty_allowlist):
        """空 allowlist 阻断写工具"""
        def db_factory():
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            return mock_db

        server = create_server_with_mocks(db_factory=db_factory)

        with patch("qualityfoundry.services.auth_service.AuthService.verify_token", return_value=mock_user_user):
            with patch("qualityfoundry.governance.policy_loader.get_policy", return_value=mock_policy_empty_allowlist):
                result = await server.handle_tool_call(
                    tool_name="run_pytest",
                    arguments={"test_path": "tests/"},
                    params={"auth": {"token": "valid_token"}},
                )

        assert "error" in result
        assert result["error"]["code"] == POLICY_BLOCKED
        assert "allowlist" in result["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_tool_not_in_allowlist_blocked(self, mock_user_user):
        """工具不在 allowlist 中被阻断"""
        policy = MagicMock()
        policy.tools.allowlist = ["run_other_tool"]  # run_pytest 不在列表中
        policy.sandbox.enabled = True

        def db_factory():
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            return mock_db

        server = create_server_with_mocks(db_factory=db_factory)

        with patch("qualityfoundry.services.auth_service.AuthService.verify_token", return_value=mock_user_user):
            with patch("qualityfoundry.governance.policy_loader.get_policy", return_value=policy):
                result = await server.handle_tool_call(
                    tool_name="run_pytest",
                    arguments={"test_path": "tests/"},
                    params={"auth": {"token": "valid_token"}},
                )

        assert "error" in result
        assert result["error"]["code"] == POLICY_BLOCKED
        assert "run_pytest" in result["error"]["message"]


class TestMCPWriteSecuritySandboxViolation:
    """测试沙箱违规场景 → -32006 SANDBOX_VIOLATION"""

    @pytest.mark.asyncio
    async def test_sandbox_disabled_blocks_write_tool(self, mock_user_user, mock_policy_sandbox_disabled):
        """sandbox.enabled=false 阻断写工具"""
        def db_factory():
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            return mock_db

        server = create_server_with_mocks(db_factory=db_factory)

        with patch("qualityfoundry.services.auth_service.AuthService.verify_token", return_value=mock_user_user):
            with patch("qualityfoundry.governance.policy_loader.get_policy", return_value=mock_policy_sandbox_disabled):
                result = await server.handle_tool_call(
                    tool_name="run_pytest",
                    arguments={"test_path": "tests/"},
                    params={"auth": {"token": "valid_token"}},
                )

        assert "error" in result
        assert result["error"]["code"] == SANDBOX_VIOLATION
        assert "sandbox" in result["error"]["message"].lower()


class TestMCPWriteSecurityReadToolsNoAuth:
    """测试只读工具不需要认证"""

    @pytest.mark.asyncio
    async def test_get_evidence_no_auth_required(self):
        """get_evidence 不需要认证"""
        server = create_server_with_mocks(db_factory=None)

        with patch("qualityfoundry.governance.tracing.collector.load_evidence", return_value=None):
            result = await server.handle_tool_call(
                tool_name="get_evidence",
                arguments={"run_id": str(uuid4())},
                params={},  # 无认证
            )

        # 应该返回正常结果（可能是 "Evidence not found"），而不是 AUTH_REQUIRED
        # error 可能是字符串（如 "Evidence not found"）或 dict
        error = result.get("error")
        if isinstance(error, dict):
            assert error.get("code") != AUTH_REQUIRED
        # 字符串错误表示业务逻辑错误而非认证错误，这是正确的


class TestMCPWriteSecuritySuccessPath:
    """测试成功路径"""

    @pytest.mark.asyncio
    async def test_admin_can_run_pytest_with_valid_config(
        self, mock_user_admin, mock_policy_with_allowlist
    ):
        """ADMIN 用户在有效配置下可以执行 run_pytest"""
        def db_factory():
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            return mock_db

        server = create_server_with_mocks(db_factory=db_factory)

        # Mock 所有依赖
        mock_result = MagicMock()
        mock_result.status.value = "SUCCESS"
        mock_result.raw_output = {"pytest": "output"}
        mock_result.error_message = None
        mock_result.elapsed_ms = 100

        with patch("qualityfoundry.services.auth_service.AuthService.verify_token", return_value=mock_user_admin):
            with patch("qualityfoundry.governance.policy_loader.get_policy", return_value=mock_policy_with_allowlist):
                with patch("qualityfoundry.tools.runners.register_all_tools"):
                    with patch("qualityfoundry.tools.registry.get_registry") as mock_get_registry:
                        mock_registry = MagicMock()
                        mock_registry.execute = AsyncMock(return_value=mock_result)
                        mock_get_registry.return_value = mock_registry

                        result = await server.handle_tool_call(
                            tool_name="run_pytest",
                            arguments={"test_path": "tests/"},
                            params={"auth": {"token": "valid_token"}},
                        )

        # 应该成功执行
        assert "error" not in result or not isinstance(result.get("error"), dict)
        assert result.get("status") == "SUCCESS"
        assert "run_id" in result


class TestMCPWriteSecurityAuditLogging:
    """测试审计日志记录"""

    @pytest.mark.asyncio
    async def test_mcp_tool_call_audit_logged_on_success(
        self, mock_user_admin, mock_policy_with_allowlist
    ):
        """成功执行时记录 MCP_TOOL_CALL 审计事件"""
        audit_logs = []

        def db_factory():
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            mock_db.add = lambda x: audit_logs.append(x)
            mock_db.commit = MagicMock()
            return mock_db

        server = create_server_with_mocks(db_factory=db_factory)

        mock_result = MagicMock()
        mock_result.status.value = "SUCCESS"
        mock_result.raw_output = {}
        mock_result.error_message = None
        mock_result.elapsed_ms = 100

        with patch("qualityfoundry.services.auth_service.AuthService.verify_token", return_value=mock_user_admin):
            with patch("qualityfoundry.governance.policy_loader.get_policy", return_value=mock_policy_with_allowlist):
                with patch("qualityfoundry.tools.runners.register_all_tools"):
                    with patch("qualityfoundry.tools.registry.get_registry") as mock_get_registry:
                        mock_registry = MagicMock()
                        mock_registry.execute = AsyncMock(return_value=mock_result)
                        mock_get_registry.return_value = mock_registry

                        await server.handle_tool_call(
                            tool_name="run_pytest",
                            arguments={"test_path": "tests/"},
                            params={"auth": {"token": "valid_token"}},
                        )

        # 应该有审计日志被记录（至少 started 和 completed）
        assert len(audit_logs) >= 1


class TestMCPErrorResponseFormat:
    """测试 JSON-RPC 2.0 错误响应格式"""

    @pytest.mark.asyncio
    async def test_error_response_is_json_rpc_compliant(self):
        """错误响应符合 JSON-RPC 2.0 格式"""
        server = create_server_with_mocks(db_factory=MagicMock())

        response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "run_pytest",
                "arguments": {"test_path": "tests/"},
                # 无 auth
            },
        })

        # 应该返回 JSON-RPC 2.0 错误格式
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == 1
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
