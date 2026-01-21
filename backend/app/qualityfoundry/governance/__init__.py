"""QualityFoundry - Governance Layer

治理层：提供证据链、门禁决策、成本控制等治理能力。

核心组件：
- tracing: 证据收集与追溯
- gate: 门禁决策（PASS/FAIL/NEED_HITL）
"""

from qualityfoundry.governance.gate import (
    GateDecision,
    GateResult,
    evaluate_gate,
    evaluate_gate_with_hitl,
)
from qualityfoundry.governance.tracing import (
    Evidence,
    EvidenceSummary,
    ToolCallSummary,
    TraceCollector,
)

__all__ = [
    # Gate
    "GateDecision",
    "GateResult",
    "evaluate_gate",
    "evaluate_gate_with_hitl",
    # Tracing
    "Evidence",
    "EvidenceSummary",
    "ToolCallSummary",
    "TraceCollector",
]
