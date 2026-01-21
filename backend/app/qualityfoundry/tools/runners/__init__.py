"""QualityFoundry - Tool Runners

统一工具执行器，将各种执行能力包装为标准 ToolResult 格式。

包含工具：
- run_playwright: 浏览器自动化（DSL actions）
- run_pytest: pytest 测试执行
- fetch_logs: 日志获取
"""

from qualityfoundry.tools.runners.log_fetcher import fetch_logs
from qualityfoundry.tools.runners.playwright_tool import run_playwright
from qualityfoundry.tools.runners.pytest_runner import run_pytest

__all__ = ["run_playwright", "run_pytest", "fetch_logs"]
