"""QualityFoundry - Gate Decision (门禁决策)

基于 Evidence 做出门禁决策：PASS / FAIL / NEED_HITL

规则（MVP 硬编码版本）：
1. 高危关键词 → NEED_HITL
2. 有 JUnit summary：errors==0 && failures==0 → PASS，否则 FAIL
3. 无 summary：所有 tool_calls.status == success → PASS，否则 FAIL
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from qualityfoundry.governance.tracing.collector import Evidence

logger = logging.getLogger(__name__)


class GateDecision(str, Enum):
    """门禁决策结果"""
    PASS = "PASS"
    FAIL = "FAIL"
    NEED_HITL = "NEED_HITL"


# 高危关键词（触发 HITL）
# 基于 input_nl 检测，不是 args
HIGH_RISK_KEYWORDS = frozenset({
    "delete",
    "drop",
    "truncate",
    "remove",
    "destroy",
    "prod",
    "production",
    "master",
    "main",
    "release",
    "deploy",
    "rollback",
    "migration",
    "schema",
    "database",
    "db",
})

# 高危模式（正则）
HIGH_RISK_PATTERNS = [
    r"\bprod\b",
    r"\bproduction\b",
    r"\bdelete\s+from\b",
    r"\bdrop\s+table\b",
    r"\btruncate\b",
    r"\brm\s+-rf\b",
    r"\bsudo\b",
]


class GateResult(BaseModel):
    """门禁决策结果"""
    model_config = ConfigDict(extra="forbid")

    decision: GateDecision
    reason: str
    approval_id: UUID | None = None
    triggered_rules: list[str] = Field(default_factory=list)
    evidence_summary: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return self.decision == GateDecision.PASS

    @property
    def needs_approval(self) -> bool:
        return self.decision == GateDecision.NEED_HITL


def evaluate_gate(evidence: Evidence) -> GateResult:
    """评估门禁

    Args:
        evidence: 证据对象

    Returns:
        GateResult: 门禁决策结果
    """
    triggered_rules: list[str] = []
    evidence_summary = None

    if evidence.summary:
        evidence_summary = evidence.summary.model_dump()

    # Rule 1: 高危关键词检测 → NEED_HITL
    hitl_reason = _check_high_risk(evidence.input_nl)
    if hitl_reason:
        triggered_rules.append(f"high_risk_keyword:{hitl_reason}")
        return GateResult(
            decision=GateDecision.NEED_HITL,
            reason=f"High-risk keyword detected: {hitl_reason}",
            triggered_rules=triggered_rules,
            evidence_summary=evidence_summary,
        )

    # Rule 2: 基于 JUnit summary 判断
    if evidence.summary and evidence.summary.tests > 0:
        if evidence.summary.errors == 0 and evidence.summary.failures == 0:
            triggered_rules.append("junit_all_passed")
            return GateResult(
                decision=GateDecision.PASS,
                reason=f"All {evidence.summary.tests} tests passed",
                triggered_rules=triggered_rules,
                evidence_summary=evidence_summary,
            )
        else:
            triggered_rules.append("junit_has_failures")
            failed_count = evidence.summary.failures + evidence.summary.errors
            return GateResult(
                decision=GateDecision.FAIL,
                reason=f"{failed_count} test(s) failed out of {evidence.summary.tests}",
                triggered_rules=triggered_rules,
                evidence_summary=evidence_summary,
            )

    # Rule 3: Fallback 到 tool_calls 状态
    if evidence.tool_calls:
        failed_tools = [tc for tc in evidence.tool_calls if tc.status != "success"]
        if not failed_tools:
            triggered_rules.append("all_tools_succeeded")
            return GateResult(
                decision=GateDecision.PASS,
                reason="All tool executions succeeded",
                triggered_rules=triggered_rules,
                evidence_summary=evidence_summary,
            )
        else:
            triggered_rules.append("tool_execution_failed")
            failed_names = [tc.tool_name for tc in failed_tools]
            return GateResult(
                decision=GateDecision.FAIL,
                reason=f"Tool(s) failed: {', '.join(failed_names)}",
                triggered_rules=triggered_rules,
                evidence_summary=evidence_summary,
            )

    # Rule 4: 无执行数据 → FAIL
    triggered_rules.append("no_execution_data")
    return GateResult(
        decision=GateDecision.FAIL,
        reason="No execution data available",
        triggered_rules=triggered_rules,
        evidence_summary=evidence_summary,
    )


def _check_high_risk(input_nl: str) -> str | None:
    """检查输入是否包含高危关键词

    Returns:
        触发的关键词/模式，如果没有触发返回 None
    """
    text_lower = input_nl.lower()

    # 检查关键词
    words = set(re.findall(r"\b\w+\b", text_lower))
    matched_keywords = words & HIGH_RISK_KEYWORDS
    if matched_keywords:
        # 只返回最重要的（优先返回 prod/production）
        priority_keywords = ["production", "prod", "delete", "drop", "truncate"]
        for kw in priority_keywords:
            if kw in matched_keywords:
                return kw
        return matched_keywords.pop()

    # 检查模式
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, text_lower):
            return f"pattern:{pattern}"

    return None


def create_hitl_approval(
    evidence: Evidence,
    gate_result: GateResult,
) -> UUID | None:
    """创建 HITL 审批记录

    注意：这是一个占位实现。PR-4 将与现有 ApprovalService 集成。

    Args:
        evidence: 证据对象
        gate_result: 门禁决策结果

    Returns:
        approval_id: 审批记录 ID
    """
    # TODO: PR-4 集成 ApprovalService
    # 目前只返回 None，实际集成时会创建 Approval 记录
    from uuid import uuid4

    if gate_result.decision != GateDecision.NEED_HITL:
        return None

    # 模拟创建审批
    approval_id = uuid4()
    logger.info(f"HITL approval created: {approval_id} for run {evidence.run_id}")

    return approval_id


def evaluate_gate_with_hitl(evidence: Evidence) -> GateResult:
    """评估门禁并在需要时创建 HITL 审批

    这是便捷方法，组合了 evaluate_gate 和 create_hitl_approval。

    Args:
        evidence: 证据对象

    Returns:
        GateResult: 包含 approval_id（如果需要 HITL）
    """
    result = evaluate_gate(evidence)

    if result.decision == GateDecision.NEED_HITL:
        approval_id = create_hitl_approval(evidence, result)
        result.approval_id = approval_id

    return result
