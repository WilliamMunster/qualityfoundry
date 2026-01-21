"""QualityFoundry - Tool Runners

统一工具执行器，将各种执行能力包装为标准 ToolResult 格式。
"""

from qualityfoundry.tools.runners.playwright_tool import run_playwright

__all__ = ["run_playwright"]
