"""Tests for Tool Allowlist Policy Enforcement (PR-B)

验证策略驱动的工具白名单执行。
"""

from uuid import uuid4

import pytest

from qualityfoundry.governance.policy_loader import PolicyConfig, ToolsPolicy
from qualityfoundry.tools.contracts import ToolRequest, ToolResult, ToolStatus
from qualityfoundry.tools.registry import ToolRegistry, reset_registry


@pytest.fixture
def registry():
    """创建独立的 registry 实例"""
    return ToolRegistry()


@pytest.fixture(autouse=True)
def reset_global_registry():
    """每个测试后重置全局 registry"""
    yield
    reset_registry()


@pytest.fixture
def dummy_tool():
    """创建一个简单的测试工具"""
    async def _tool(req: ToolRequest) -> ToolResult:
        return ToolResult.success(stdout="executed")
    return _tool


class TestToolAllowlistEnforcement:
    """工具白名单策略执行测试"""

    @pytest.mark.asyncio
    async def test_tool_allowed_by_policy(self, registry: ToolRegistry, dummy_tool):
        """白名单中的工具可以执行"""
        registry.register("allowed_tool", dummy_tool)

        policy = PolicyConfig(
            tools=ToolsPolicy(allowlist=["allowed_tool", "another_tool"])
        )

        request = ToolRequest(tool_name="allowed_tool", run_id=uuid4())
        result = await registry.execute("allowed_tool", request, policy=policy)

        assert result.status == ToolStatus.SUCCESS
        assert result.stdout == "executed"

    @pytest.mark.asyncio
    async def test_tool_blocked_by_policy(self, registry: ToolRegistry, dummy_tool):
        """不在白名单中的工具被阻断"""
        registry.register("blocked_tool", dummy_tool)

        policy = PolicyConfig(
            tools=ToolsPolicy(allowlist=["other_tool"])
        )

        request = ToolRequest(tool_name="blocked_tool", run_id=uuid4())
        result = await registry.execute("blocked_tool", request, policy=policy)

        assert result.status == ToolStatus.FAILED
        assert "not in policy allowlist" in result.error_message
        assert result.raw_output["decision_source"] == "policy_block"

    @pytest.mark.asyncio
    async def test_empty_allowlist_allows_all(self, registry: ToolRegistry, dummy_tool):
        """空白名单允许所有工具"""
        registry.register("any_tool", dummy_tool)

        policy = PolicyConfig(tools=ToolsPolicy(allowlist=[]))

        request = ToolRequest(tool_name="any_tool", run_id=uuid4())
        result = await registry.execute("any_tool", request, policy=policy)

        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_no_policy_allows_all(self, registry: ToolRegistry, dummy_tool):
        """无策略时允许所有工具（向后兼容）"""
        registry.register("any_tool", dummy_tool)

        request = ToolRequest(tool_name="any_tool", run_id=uuid4())
        result = await registry.execute("any_tool", request, policy=None)

        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_blocked_tool_produces_evidence(self, registry: ToolRegistry, dummy_tool):
        """被阻断的工具产出可追溯的证据"""
        registry.register("dangerous_tool", dummy_tool)

        policy = PolicyConfig(
            tools=ToolsPolicy(allowlist=["safe_tool"])
        )

        request = ToolRequest(tool_name="dangerous_tool", run_id=uuid4())
        result = await registry.execute("dangerous_tool", request, policy=policy)

        # 验证决策来源可追溯
        assert result.raw_output is not None
        assert result.raw_output["decision_source"] == "policy_block"
        assert result.error_message is not None
