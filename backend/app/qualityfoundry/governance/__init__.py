"""QualityFoundry - Governance Layer

治理层：提供证据链、门禁决策、成本控制等治理能力。

核心组件：
- tracing: 证据收集与追溯
- gate: 门禁决策（PASS/FAIL/NEED_HITL）
- policy_loader: L1 策略配置加载
"""

from qualityfoundry.governance.gate import (
    GateDecision,
    GateResult,
    evaluate_gate,
    evaluate_gate_with_hitl,
)
from qualityfoundry.governance.policy_loader import (
    PolicyConfig,
    get_policy,
    load_policy,
    clear_policy_cache,
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
    # Policy (L1)
    "PolicyConfig",
    "get_policy",
    "load_policy",
    "clear_policy_cache",
    # Tracing
    "Evidence",
    "EvidenceSummary",
    "ToolCallSummary",
    "TraceCollector",
]
