"""QualityFoundry - Tracing (证据链)

证据收集与追溯模块。

核心组件：
- junit_parser: JUnit XML 解析
- collector: 证据收集器（生成 evidence.json）
"""

from qualityfoundry.governance.tracing.collector import (
    Evidence,
    EvidenceSummary,
    ToolCallSummary,
    TraceCollector,
)
from qualityfoundry.governance.tracing.junit_parser import (
    JUnitSummary,
    parse_junit_xml,
)

__all__ = [
    "Evidence",
    "EvidenceSummary",
    "ToolCallSummary",
    "TraceCollector",
    "JUnitSummary",
    "parse_junit_xml",
]
