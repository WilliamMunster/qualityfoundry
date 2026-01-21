"""QualityFoundry - Unified Tool System

统一工具层：为所有执行工具提供标准化的输入/输出契约。

核心组件：
- contracts: ToolRequest/ToolResult/ArtifactRef 数据契约
- registry: 工具注册表
- base: 统一执行封装（超时、日志、artifact 落盘）
- runners: 工具实现（run_playwright, run_pytest 等）
"""

from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolMetrics,
    ToolRequest,
    ToolResult,
    ToolStatus,
)
from qualityfoundry.tools.registry import ToolRegistry, get_registry, ToolNotFoundError
from qualityfoundry.tools.base import (
    ToolExecutionContext,
    get_artifact_dir,
    collect_artifacts,
    log_tool_result,
)

__all__ = [
    # Contracts
    "ArtifactRef",
    "ArtifactType",
    "ToolMetrics",
    "ToolRequest",
    "ToolResult",
    "ToolStatus",
    # Registry
    "ToolRegistry",
    "ToolNotFoundError",
    "get_registry",
    # Base
    "ToolExecutionContext",
    "get_artifact_dir",
    "collect_artifacts",
    "log_tool_result",
]
