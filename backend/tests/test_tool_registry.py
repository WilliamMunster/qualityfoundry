"""Tests for Tool Registry (PR-1)

验证工具注册表的正确性。
"""

from uuid import uuid4

import pytest

from qualityfoundry.tools.contracts import ToolRequest, ToolResult, ToolStatus
from qualityfoundry.tools.registry import (
    ToolNotFoundError,
    ToolRegistry,
    get_registry,
    reset_registry,
)


@pytest.fixture
def registry():
    """创建独立的 registry 实例"""
    return ToolRegistry()


@pytest.fixture(autouse=True)
def reset_global_registry():
    """每个测试后重置全局 registry"""
    yield
    reset_registry()


class TestToolRegistry:
    """ToolRegistry 测试"""

    def test_register_and_get(self, registry: ToolRegistry):
        """注册和获取"""

        async def dummy_tool(req: ToolRequest) -> ToolResult:
            return ToolResult.success()

        registry.register("dummy", dummy_tool, description="A dummy tool")

        assert registry.exists("dummy")
        assert registry.get("dummy") == dummy_tool

    def test_register_with_metadata(self, registry: ToolRegistry):
        """注册时携带元数据"""

        async def my_tool(req: ToolRequest) -> ToolResult:
            return ToolResult.success()

        registry.register(
            "my_tool",
            my_tool,
            description="My tool description",
            version="2.0.0",
            tags=["test", "demo"],
        )

        metadata = registry.get_metadata("my_tool")
        assert metadata is not None
        assert metadata["name"] == "my_tool"
        assert metadata["description"] == "My tool description"
        assert metadata["version"] == "2.0.0"
        assert "test" in metadata["tags"]

    def test_get_nonexistent(self, registry: ToolRegistry):
        """获取不存在的工具"""
        with pytest.raises(ToolNotFoundError) as exc_info:
            registry.get("nonexistent")
        assert exc_info.value.tool_name == "nonexistent"

    def test_unregister(self, registry: ToolRegistry):
        """注销工具"""

        async def tool(req: ToolRequest) -> ToolResult:
            return ToolResult.success()

        registry.register("temp_tool", tool)
        assert registry.exists("temp_tool")

        result = registry.unregister("temp_tool")
        assert result is True
        assert not registry.exists("temp_tool")

        # 再次注销返回 False
        result = registry.unregister("temp_tool")
        assert result is False

    def test_list_tools(self, registry: ToolRegistry):
        """列出工具"""

        async def tool1(req: ToolRequest) -> ToolResult:
            return ToolResult.success()

        async def tool2(req: ToolRequest) -> ToolResult:
            return ToolResult.success()

        registry.register("tool1", tool1)
        registry.register("tool2", tool2)

        tools = registry.list_tools()
        assert "tool1" in tools
        assert "tool2" in tools
        assert len(tools) == 2

    def test_list_metadata(self, registry: ToolRegistry):
        """列出所有元数据"""

        async def tool(req: ToolRequest) -> ToolResult:
            return ToolResult.success()

        registry.register("t1", tool, description="Tool 1")
        registry.register("t2", tool, description="Tool 2")

        all_metadata = registry.list_metadata()
        assert len(all_metadata) == 2
        names = [m["name"] for m in all_metadata]
        assert "t1" in names
        assert "t2" in names

    @pytest.mark.asyncio
    async def test_execute_success(self, registry: ToolRegistry):
        """执行成功"""

        async def echo_tool(req: ToolRequest) -> ToolResult:
            msg = req.args.get("message", "")
            return ToolResult.success(stdout=msg)

        registry.register("echo", echo_tool)

        request = ToolRequest(
            tool_name="echo",
            run_id=uuid4(),
            args={"message": "Hello, World!"},
        )
        result = await registry.execute("echo", request)

        assert result.status == ToolStatus.SUCCESS
        assert result.stdout == "Hello, World!"

    @pytest.mark.asyncio
    async def test_execute_exception(self, registry: ToolRegistry):
        """执行时抛出异常"""

        async def failing_tool(req: ToolRequest) -> ToolResult:
            raise ValueError("Something went wrong")

        registry.register("failing", failing_tool)

        request = ToolRequest(
            tool_name="failing",
            run_id=uuid4(),
        )
        result = await registry.execute("failing", request)

        assert result.status == ToolStatus.FAILED
        assert "Something went wrong" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_nonexistent(self, registry: ToolRegistry):
        """执行不存在的工具"""
        request = ToolRequest(
            tool_name="nonexistent",
            run_id=uuid4(),
        )
        with pytest.raises(ToolNotFoundError):
            await registry.execute("nonexistent", request)

    def test_decorator_registration(self, registry: ToolRegistry):
        """装饰器注册"""

        @registry.decorator("decorated_tool", description="Decorated", version="1.2.3")
        async def my_decorated_tool(req: ToolRequest) -> ToolResult:
            return ToolResult.success()

        assert registry.exists("decorated_tool")
        metadata = registry.get_metadata("decorated_tool")
        assert metadata["version"] == "1.2.3"


class TestGlobalRegistry:
    """全局 Registry 测试"""

    def test_singleton(self):
        """单例模式"""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reset(self):
        """重置"""
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2
