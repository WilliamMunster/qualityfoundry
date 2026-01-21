"""QualityFoundry - Tool Runners

统一工具执行器，将各种执行能力包装为标准 ToolResult 格式。

包含工具：
- run_playwright: 浏览器自动化（DSL actions）
- run_pytest: pytest 测试执行
- fetch_logs: 日志获取

导入此模块时会自动注册所有工具到全局注册表。
"""

from qualityfoundry.tools.registry import get_registry
from qualityfoundry.tools.runners.log_fetcher import fetch_logs, TOOL_METADATA as FETCH_LOGS_METADATA
from qualityfoundry.tools.runners.playwright_tool import run_playwright
from qualityfoundry.tools.runners.pytest_runner import run_pytest, TOOL_METADATA as PYTEST_METADATA


def register_all_tools():
    """注册所有内置工具到全局注册表"""
    registry = get_registry()

    # 注册 pytest runner
    registry.register(
        name=PYTEST_METADATA["name"],
        fn=run_pytest,
        description=PYTEST_METADATA["description"],
        version=PYTEST_METADATA["version"],
        tags=PYTEST_METADATA["tags"],
    )

    # 注册 fetch_logs
    if not registry.exists("fetch_logs"):
        registry.register(
            name=FETCH_LOGS_METADATA["name"],
            fn=fetch_logs,
            description=FETCH_LOGS_METADATA["description"],
            version=FETCH_LOGS_METADATA["version"],
            tags=FETCH_LOGS_METADATA["tags"],
        )

    # run_playwright 需要检查元数据
    if not registry.exists("run_playwright"):
        registry.register(
            name="run_playwright",
            fn=run_playwright,
            description="Execute Playwright browser automation",
            version="1.0.0",
            tags=["testing", "e2e", "playwright"],
        )


# 模块加载时自动注册
register_all_tools()

__all__ = ["run_playwright", "run_pytest", "fetch_logs", "register_all_tools"]
