"""QualityFoundry - Governance Layer

治理层：提供证据链、门禁决策、成本控制等治理能力。

核心组件：
- tracing: 证据收集与追溯
- gate: 门禁决策（PASS/FAIL/NEED_HITL）
- policy_loader: L1 策略配置加载
- repro: 可复现性元数据
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
from qualityfoundry.governance.repro import (
    ReproMeta,
    get_repro_meta,
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
    # Repro (L5 foundation)
    "ReproMeta",
    "get_repro_meta",
    # Tracing
    "Evidence",
    "EvidenceSummary",
    "ToolCallSummary",
    "TraceCollector",
]
