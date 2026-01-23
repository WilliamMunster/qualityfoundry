"""QualityFoundry - Tool Registry (工具注册表)

统一的工具注册和发现机制。

使用方式：
    registry = get_registry()
    registry.register("run_playwright", playwright_tool_fn)
    result = await registry.execute("run_playwright", request)
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from qualityfoundry.governance.policy_loader import PolicyConfig

from qualityfoundry.tools.contracts import ToolRequest, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# 工具函数类型：接收 ToolRequest，返回 ToolResult
ToolFunction: TypeAlias = Callable[[ToolRequest], Awaitable[ToolResult]]


class ToolNotFoundError(Exception):
    """工具未找到异常"""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        # 保持英文异常信息以兼容现有倾向于英文正则匹配的测试
        super().__init__(f"Tool not found: {tool_name}")


class ToolRegistry:
    """工具注册表

    提供工具的注册、发现和执行功能。
    """

    def __init__(self):
        self._tools: dict[str, ToolFunction] = {}
        self._metadata: dict[str, dict] = {}

    def register(
        self,
        name: str,
        fn: ToolFunction,
        *,
        description: str = "",
        version: str = "1.0.0",
        tags: list[str] | None = None,
    ) -> None:
        """注册工具

        Args:
            name: 工具名称（唯一标识）
            fn: 工具函数（async）
            description: 工具描述
            version: 版本号
            tags: 标签列表
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")

        self._tools[name] = fn
        self._metadata[name] = {
            "name": name,
            "description": description,
            "version": version,
            "tags": tags or [],
        }
        logger.info(f"Registered tool: {name} (v{version})")

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            del self._metadata[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> ToolFunction:
        """获取工具函数

        Raises:
            ToolNotFoundError: 工具未找到
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def exists(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    def list_tools(self) -> list[str]:
        """列出所有已注册工具名称"""
        return list(self._tools.keys())

    def get_metadata(self, name: str) -> dict | None:
        """获取工具元数据"""
        return self._metadata.get(name)

    def list_metadata(self) -> list[dict]:
        """列出所有工具元数据"""
        return list(self._metadata.values())

    async def execute(
        self,
        name: str,
        request: ToolRequest,
        *,
        policy: "PolicyConfig | None" = None,
    ) -> ToolResult:
        """执行工具

        Args:
            name: 工具名称
            request: 工具请求
            policy: 策略配置（可选，用于 allowlist 检查）

        Returns:
            ToolResult: 执行结果

        Raises:
            ToolNotFoundError: 工具未找到
        """
        # Allowlist enforcement
        if policy is not None and policy.tools.allowlist:
            if name not in policy.tools.allowlist:
                logger.warning(f"Tool '{name}' blocked by policy allowlist")
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error_message=f"Tool '{name}' not in policy allowlist",
                    raw_output={"decision_source": "policy_block"},
                )

        fn = self.get(name)
        logger.info(f"Executing tool: {name}, run_id={request.run_id}")

        try:
            result = await fn(request)
            logger.info(f"Tool {name} completed: status={result.status.value}")
            return result
        except Exception as e:
            logger.exception(f"Tool {name} raised exception")
            return ToolResult.failed(
                error_message=str(e),
            )

    def decorator(
        self,
        name: str,
        *,
        description: str = "",
        version: str = "1.0.0",
        tags: list[str] | None = None,
    ):
        """装饰器方式注册工具

        用法:
            @registry.decorator("my_tool", description="My tool")
            async def my_tool(request: ToolRequest) -> ToolResult:
                ...
        """

        def wrapper(fn: ToolFunction) -> ToolFunction:
            self.register(name, fn, description=description, version=version, tags=tags)
            return fn

        return wrapper


# 全局单例
_global_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册表单例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_registry() -> None:
    """重置全局注册表（用于测试）"""
    global _global_registry
    _global_registry = None
