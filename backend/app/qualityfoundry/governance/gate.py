"""QualityFoundry - Gate Decision (门禁决策)

基于 Evidence 做出门禁决策：PASS / FAIL / NEED_HITL

规则（L1 Policy 配置驱动版本）：
1. 高危关键词 → NEED_HITL（从 policy_config.yaml 加载）
2. 有 JUnit summary：按 policy 阈值判断 → PASS / FAIL
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
from qualityfoundry.governance.policy_loader import PolicyConfig, get_policy
from qualityfoundry.governance.ai_review import (
    AIReviewConfig,
    AIReviewEngine,
    StrategyType,
    ModelConfig as AIModelConfig,
)

logger = logging.getLogger(__name__)


class GateDecision(str, Enum):
    """门禁决策结果"""
    PASS = "PASS"
    FAIL = "FAIL"
    NEED_HITL = "NEED_HITL"


# ==================== 保留用于向后兼容 ====================
# 以下常量已废弃，请使用 PolicyConfig 替代
# 仅用于未传入 policy 时的默认回退
_LEGACY_HIGH_RISK_KEYWORDS = frozenset({
    "delete", "drop", "truncate", "remove", "destroy",
    "prod", "production", "master", "main", "release",
    "deploy", "rollback", "migration", "schema", "database", "db",
})

_LEGACY_HIGH_RISK_PATTERNS = [
    r"\bprod\b", r"\bproduction\b", r"\bdelete\s+from\b",
    r"\bdrop\s+table\b", r"\btruncate\b", r"\brm\s+-rf\b", r"\bsudo\b",
]


class GateResult(BaseModel):
    """门禁决策结果"""
    model_config = ConfigDict(extra="forbid")

    decision: GateDecision
    reason: str
    approval_id: UUID | None = None
    triggered_rules: list[str] = Field(default_factory=list)
    evidence_summary: dict[str, Any] | None = None
    ai_review_result: dict[str, Any] | None = None  # AI 评审结果

    @property
    def passed(self) -> bool:
        return self.decision == GateDecision.PASS

    @property
    def needs_approval(self) -> bool:
        return self.decision == GateDecision.NEED_HITL


def evaluate_gate(
    evidence: Evidence,
    policy: PolicyConfig | None = None,
) -> GateResult:
    """评估门禁

    Args:
        evidence: 证据对象
        policy: 策略配置（可选，默认从文件加载）

    Returns:
        GateResult: 门禁决策结果
    """
    # 加载策略
    if policy is None:
        policy = get_policy()

    triggered_rules: list[str] = []
    evidence_summary = None

    if evidence.summary:
        evidence_summary = evidence.summary.model_dump()

    # 规则 1: 高危关键词检测 → NEED_HITL（使用 policy 配置）
    hitl_reason = _check_high_risk(evidence.input_nl, policy)
    if hitl_reason:
        triggered_rules.append(f"high_risk_keyword:{hitl_reason}")
        return GateResult(
            decision=GateDecision.NEED_HITL,
            reason=f"检测到高危关键词: {hitl_reason}",
            triggered_rules=triggered_rules,
            evidence_summary=evidence_summary,
        )

    # 规则 2: 基于 JUnit summary 判断（使用 policy 阈值）
    if evidence.summary and evidence.summary.tests > 0:
        max_f = policy.junit_pass_rule.max_failures
        max_e = policy.junit_pass_rule.max_errors
        if evidence.summary.errors <= max_e and evidence.summary.failures <= max_f:
            triggered_rules.append("junit_all_passed")
            return GateResult(
                decision=GateDecision.PASS,
                reason=f"所有 {evidence.summary.tests} 个测试已通过",
                triggered_rules=triggered_rules,
                evidence_summary=evidence_summary,
            )
        else:
            triggered_rules.append("junit_has_failures")
            failed_count = evidence.summary.failures + evidence.summary.errors
            return GateResult(
                decision=GateDecision.FAIL,
                reason=f"{evidence.summary.tests} 个测试中共有 {failed_count} 个失败",
                triggered_rules=triggered_rules,
                evidence_summary=evidence_summary,
            )

    # 规则 3: Fallback 到 tool_calls 状态（使用 policy 配置）
    if evidence.tool_calls:
        if policy.fallback_rule.require_all_tools_success:
            failed_tools = [tc for tc in evidence.tool_calls if tc.status != "success"]
            if not failed_tools:
                triggered_rules.append("all_tools_succeeded")
                return GateResult(
                    decision=GateDecision.PASS,
                    reason="所有工具执行成功",
                    triggered_rules=triggered_rules,
                    evidence_summary=evidence_summary,
                )
            else:
                triggered_rules.append("tool_execution_failed")
                failed_reasons = []
                for tc in failed_tools:
                    msg = f"{tc.tool_name}"
                    if tc.error_message:
                        # 只取前 100 个字符避免过长
                        err_snippet = tc.error_message[:100].replace("\n", " ")
                        msg += f" ({err_snippet})"
                    failed_reasons.append(msg)
                
                return GateResult(
                    decision=GateDecision.FAIL,
                    reason=f"工具执行失败: {'; '.join(failed_reasons)}",
                    triggered_rules=triggered_rules,
                    evidence_summary=evidence_summary,
                )
        else:
            # 不要求所有工具成功，则视为 PASS
            triggered_rules.append("fallback_no_strict_check")
            return GateResult(
                decision=GateDecision.PASS,
                reason="后备规则通过 (无严格工具检查)",
                triggered_rules=triggered_rules,
                evidence_summary=evidence_summary,
            )

    # 规则 4: 无执行数据 → FAIL
    triggered_rules.append("no_execution_data")
    return GateResult(
        decision=GateDecision.FAIL,
        reason="无可用执行数据",
        triggered_rules=triggered_rules,
        evidence_summary=evidence_summary,
    )


def _build_review_content(evidence: Evidence) -> str:
    """构建 AI 评审内容

    将证据转换为可供 AI 评审的文本格式。

    Args:
        evidence: 证据对象

    Returns:
        评审内容文本
    """
    content_parts = []

    if evidence.input_nl:
        content_parts.append(f"User Request: {evidence.input_nl}")

    if evidence.summary:
        content_parts.append(
            f"Test Results: {evidence.summary.tests} tests, "
            f"{evidence.summary.failures} failures, "
            f"{evidence.summary.errors} errors"
        )

    if evidence.tool_calls:
        tool_summary = []
        for tc in evidence.tool_calls:
            status = "✓" if tc.status == "success" else "✗"
            tool_summary.append(f"{status} {tc.tool_name}")
        content_parts.append(f"Tool Executions: {', '.join(tool_summary)}")

    return "\n".join(content_parts) if content_parts else "No evidence available"


def evaluate_gate_with_ai_review(
    evidence: Evidence,
    policy: PolicyConfig | None = None,
) -> GateResult:
    """评估门禁（含 AI 评审）

    在标准门禁评估基础上，如果 policy.ai_review.enabled=True，
    则启用 AI 评审作为额外决策因子。

    Args:
        evidence: 证据对象
        policy: 策略配置（可选）

    Returns:
        GateResult: 门禁决策结果（含 ai_review_result）
    """
    # 先执行标准门禁评估
    result = evaluate_gate(evidence, policy)

    # 加载策略
    if policy is None:
        policy = get_policy()

    # 如果 AI 评审未启用，直接返回标准结果
    if not policy.ai_review.enabled:
        return result

    # AI 评审已启用，执行评审
    try:
        # 构建 AI 评审配置
        ai_config = AIReviewConfig(
            enabled=True,
            models=[
                AIModelConfig(
                    name=m.name,
                    provider=m.provider,
                    weight=m.weight,
                    temperature=m.temperature,
                )
                for m in policy.ai_review.models
            ],
            strategy=StrategyType(policy.ai_review.strategy),
            pass_threshold=policy.ai_review.thresholds.pass_confidence,
            hitl_threshold=policy.ai_review.thresholds.hitl_confidence,
            max_retries=policy.ai_review.max_retries,
            timeout_seconds=policy.ai_review.timeout_seconds,
        )

        # 创建引擎并执行评审
        engine = AIReviewEngine(ai_config)
        review_content = _build_review_content(evidence)
        ai_result = engine.review(review_content)

        # 将 AI 评审结果附加到 GateResult
        result.ai_review_result = ai_result.to_evidence_format().get("ai_review")

        # AI 评审触发 HITL 的情况
        if ai_result.hitl_triggered or ai_result.verdict.value == "NEEDS_HITL":
            # 如果已有 NEED_HITL，保留原决策但添加 AI 评审信息
            if result.decision != GateDecision.NEED_HITL:
                result.decision = GateDecision.NEED_HITL
                result.reason = f"[AI Review] {ai_result.reasoning}"
                result.triggered_rules.append("ai_review_triggered_hitl")
            else:
                result.triggered_rules.append("ai_review_concurs")

        # AI 评审FAIL的情况（除非已有更严重的决策）
        elif ai_result.verdict.value == "FAIL" and result.decision == GateDecision.PASS:
            result.decision = GateDecision.FAIL
            result.reason = f"[AI Review] {ai_result.reasoning}"
            result.triggered_rules.append("ai_review_failed")

        # AI 评审通过的情况
        elif ai_result.verdict.value == "PASS":
            result.triggered_rules.append("ai_review_passed")

    except Exception as e:
        logger.warning(f"AI review failed, falling back to standard gate: {e}")
        result.triggered_rules.append("ai_review_error")

    return result


def _check_high_risk(
    input_nl: str,
    policy: PolicyConfig | None = None,
) -> str | None:
    """检查输入是否包含高危关键词

    Args:
        input_nl: 自然语言输入
        policy: 策略配置（可选）

    Returns:
        触发的关键词/模式，如果没有触发返回 None
    """
    # 获取关键词和模式
    if policy:
        keywords = frozenset(policy.high_risk_keywords)
        patterns = policy.high_risk_patterns
    else:
        keywords = _LEGACY_HIGH_RISK_KEYWORDS
        patterns = _LEGACY_HIGH_RISK_PATTERNS

    text_lower = input_nl.lower()

    # 检查关键词
    words = set(re.findall(r"\b\w+\b", text_lower))
    matched_keywords = words & keywords
    if matched_keywords:
        # 只返回最重要的（优先返回 prod/production）
        priority_keywords = ["production", "prod", "delete", "drop", "truncate"]
        for kw in priority_keywords:
            if kw in matched_keywords:
                return kw
        return matched_keywords.pop()

    # 检查模式
    for pattern in patterns:
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
