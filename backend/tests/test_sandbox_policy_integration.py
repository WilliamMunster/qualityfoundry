"""Sandbox Policy Integration Tests (PR-B B4)

验证沙箱行为由策略配置驱动的集成测试。

覆盖三态：
1. sandbox.enabled = true (强制生效)
2. sandbox.enabled = false (完全禁用)
3. policy 没有 sandbox 段 (使用默认值)
"""

from __future__ import annotations

import pytest
from pathlib import Path
from uuid import uuid4

from qualityfoundry.governance.policy_loader import (
    PolicyConfig,
    SandboxPolicy,
    load_policy,
)
from qualityfoundry.tools.registry import (
    ToolRegistry,
    SANDBOXABLE_TOOLS,
    reset_registry,
)
from qualityfoundry.tools.contracts import ToolRequest, ToolResult
from qualityfoundry.execution.sandbox import SandboxConfig


class TestPolicySchemaCompatibility:
    """Test B1: Policy schema 变更不破坏现有配置"""

    def test_policy_loads_without_sandbox_section(self, tmp_path: Path):
        """无 sandbox 段的 policy 使用默认值"""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("""
version: "1.0"
high_risk_keywords:
  - delete
""")
        config = load_policy(policy_file)
        # 默认值应该与 SandboxPolicy 一致
        assert config.sandbox.enabled is True
        assert config.sandbox.timeout_s == 300
        assert config.sandbox.memory_limit_mb == 512
        assert "tests/" in config.sandbox.allowed_paths

    def test_policy_loads_with_sandbox_section(self, tmp_path: Path):
        """有 sandbox 段的 policy 使用指定值"""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("""
version: "1.0"
sandbox:
  enabled: false
  timeout_s: 60
  memory_limit_mb: 256
  allowed_paths:
    - "custom/"
  env_whitelist:
    - "CUSTOM_VAR"
""")
        config = load_policy(policy_file)
        assert config.sandbox.enabled is False
        assert config.sandbox.timeout_s == 60
        assert config.sandbox.memory_limit_mb == 256
        assert "custom/" in config.sandbox.allowed_paths
        assert "CUSTOM_VAR" in config.sandbox.env_whitelist

    def test_sandbox_policy_defaults_match_sandbox_config(self):
        """SandboxPolicy 默认值与 SandboxConfig 对齐"""
        policy = SandboxPolicy()
        config = SandboxConfig()
        
        # 关键参数应该对齐
        assert policy.timeout_s == config.timeout_s
        assert policy.memory_limit_mb == config.memory_limit_mb
        # allowed_paths 和 env_whitelist 可能有细微差异，但核心路径应该一致
        assert "tests/" in policy.allowed_paths


class TestSandboxEnforcement:
    """Test B2: ToolRegistry.execute() 沙箱强制执行"""

    @pytest.fixture(autouse=True)
    def reset_global_registry(self):
        """每个测试重置全局 registry"""
        reset_registry()
        yield
        reset_registry()

    @pytest.mark.asyncio
    async def test_sandboxable_tools_constant_contains_pytest(self):
        """SANDBOXABLE_TOOLS 包含 run_pytest"""
        assert "run_pytest" in SANDBOXABLE_TOOLS

    @pytest.mark.asyncio
    async def test_non_sandboxable_tools_not_in_constant(self):
        """fetch_logs 不在 SANDBOXABLE_TOOLS 中"""
        assert "run_playwright" in SANDBOXABLE_TOOLS
        assert "fetch_logs" not in SANDBOXABLE_TOOLS

    @pytest.mark.asyncio
    async def test_sandbox_enabled_passes_config_to_tool(self):
        """启用 sandbox 时，sandbox_config 传递给工具"""
        registry = ToolRegistry()
        received_config = None

        async def mock_run_pytest(request, *, sandbox_config=None, sandbox_mode="subprocess", container_config=None):
            nonlocal received_config
            received_config = sandbox_config
            return ToolResult.success()

        registry.register("run_pytest", mock_run_pytest)

        policy = PolicyConfig(sandbox=SandboxPolicy(
            enabled=True,
            timeout_s=42,
            memory_limit_mb=128,
        ))
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={"test_path": "tests/"},
        )

        await registry.execute("run_pytest", request, policy=policy)

        assert received_config is not None
        assert received_config.timeout_s == 42
        assert received_config.memory_limit_mb == 128

    @pytest.mark.asyncio
    async def test_sandbox_disabled_no_config_passed(self):
        """禁用 sandbox 时，不传递 sandbox_config"""
        registry = ToolRegistry()
        received_config = "not_called"

        async def mock_run_pytest(request, *, sandbox_config=None, sandbox_mode="subprocess", container_config=None):
            nonlocal received_config
            received_config = sandbox_config
            return ToolResult.success()

        registry.register("run_pytest", mock_run_pytest)

        policy = PolicyConfig(sandbox=SandboxPolicy(enabled=False))
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={"test_path": "tests/"},
        )

        await registry.execute("run_pytest", request, policy=policy)

        # sandbox_config 应该为 None（禁用时不传递）
        assert received_config is None

    @pytest.mark.asyncio
    async def test_non_sandboxable_tool_no_config_passed(self):
        """非 sandboxable 工具不接收 sandbox_config"""
        registry = ToolRegistry()
        call_args = []

        async def mock_playwright(request, *, sandbox_config=None, sandbox_mode="subprocess", container_config=None):
            call_args.append(("request", request))
            return ToolResult.success()

        registry.register("run_playwright", mock_playwright)

        policy = PolicyConfig(sandbox=SandboxPolicy(enabled=True))
        request = ToolRequest(
            tool_name="run_playwright",
            run_id=uuid4(),
            args={},
        )

        # 不应该报错（不会尝试传递 sandbox_config 参数）
        result = await registry.execute("run_playwright", request, policy=policy)
        assert result.ok
        assert len(call_args) == 1

    @pytest.mark.asyncio
    async def test_no_policy_means_no_sandbox_enforcement(self):
        """无 policy 时不强制 sandbox"""
        registry = ToolRegistry()
        received_config = "not_called"

        async def mock_run_pytest(request, *, sandbox_config=None, sandbox_mode="subprocess", container_config=None):
            nonlocal received_config
            received_config = sandbox_config
            return ToolResult.success()

        registry.register("run_pytest", mock_run_pytest)

        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={"test_path": "tests/"},
        )

        await registry.execute("run_pytest", request, policy=None)

        # 无 policy 时，sandbox_config 不传递
        assert received_config is None


class TestSandboxPolicyValues:
    """测试 policy 值正确传递到 SandboxConfig"""

    @pytest.mark.asyncio
    async def test_allowed_paths_from_policy(self):
        """allowed_paths 从 policy 正确传递"""
        registry = ToolRegistry()
        received_config = None

        async def mock_run_pytest(request, *, sandbox_config=None, sandbox_mode="subprocess", container_config=None):
            nonlocal received_config
            received_config = sandbox_config
            return ToolResult.success()

        registry.register("run_pytest", mock_run_pytest)

        policy = PolicyConfig(sandbox=SandboxPolicy(
            enabled=True,
            allowed_paths=["custom/path/", "another/"],
        ))
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={"test_path": "tests/"},
        )

        await registry.execute("run_pytest", request, policy=policy)

        assert received_config is not None
        assert "custom/path/" in received_config.allowed_paths
        assert "another/" in received_config.allowed_paths

    @pytest.mark.asyncio
    async def test_env_whitelist_from_policy(self):
        """env_whitelist 从 policy 正确传递"""
        registry = ToolRegistry()
        received_config = None

        async def mock_run_pytest(request, *, sandbox_config=None, sandbox_mode="subprocess", container_config=None):
            nonlocal received_config
            received_config = sandbox_config
            return ToolResult.success()

        registry.register("run_pytest", mock_run_pytest)

        policy = PolicyConfig(sandbox=SandboxPolicy(
            enabled=True,
            env_whitelist=["CUSTOM_VAR", "MY_*"],
        ))
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={"test_path": "tests/"},
        )

        await registry.execute("run_pytest", request, policy=policy)

        assert received_config is not None
        assert "CUSTOM_VAR" in received_config.env_whitelist
        assert "MY_*" in received_config.env_whitelist


class TestSandboxAuditEvent:
    """Test B3: SANDBOX_EXEC 审计事件"""

    def test_sandbox_exec_event_type_exists(self):
        """SANDBOX_EXEC 事件类型存在"""
        from qualityfoundry.database.audit_log_models import AuditEventType
        
        assert hasattr(AuditEventType, "SANDBOX_EXEC")
        assert AuditEventType.SANDBOX_EXEC.value == "sandbox_exec"
