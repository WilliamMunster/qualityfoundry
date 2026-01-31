"""Test Gate with AI Review Integration

门禁与 AI 评审集成测试
"""
import pytest
from uuid import uuid4

from qualityfoundry.governance.gate import (
    evaluate_gate,
    evaluate_gate_with_ai_review,
    GateDecision,
    _build_review_content,
)
from qualityfoundry.governance.policy_loader import (
    PolicyConfig,
    AIReviewPolicy,
    AIReviewModelConfig,
    AIReviewThresholds,
)
from qualityfoundry.governance.tracing.collector import (
    Evidence,
    EvidenceSummary,
    ToolCallSummary,
)


def _run_id():
    """生成测试用的 run_id（字符串格式）"""
    return str(uuid4())


class TestBuildReviewContent:
    """测试评审内容构建"""

    def test_build_content_with_nl_input(self):
        """构建包含自然语言输入的评审内容"""
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Run tests for login feature",
        )
        content = _build_review_content(evidence)
        assert "User Request: Run tests for login feature" in content

    def test_build_content_with_summary(self):
        """构建包含测试摘要的评审内容"""
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Test",
            summary=EvidenceSummary(
                tests=10,
                failures=1,
                errors=0,
                time=5.0,
            ),
        )
        content = _build_review_content(evidence)
        assert "Test Results: 10 tests, 1 failures, 0 errors" in content

    def test_build_content_with_tool_calls(self):
        """构建包含工具调用的评审内容"""
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Test",
            tool_calls=[
                ToolCallSummary(tool_name="run_pytest", status="success"),
                ToolCallSummary(tool_name="fetch_logs", status="failed", error_message="timeout"),
            ],
        )
        content = _build_review_content(evidence)
        assert "✓ run_pytest" in content
        assert "✗ fetch_logs" in content

    def test_build_content_empty_evidence(self):
        """空证据返回默认内容"""
        evidence = Evidence(run_id=_run_id(), input_nl="")
        content = _build_review_content(evidence)
        assert content == "No evidence available"


class TestEvaluateGateWithAIReviewDisabled:
    """测试 AI 评审禁用时的门禁评估"""

    @pytest.fixture
    def disabled_ai_policy(self):
        """AI 评审禁用的策略"""
        return PolicyConfig(
            ai_review=AIReviewPolicy(enabled=False)
        )

    @pytest.fixture
    def passing_evidence(self):
        """测试通过的 Evidence"""
        return Evidence(
            run_id=_run_id(),
            input_nl="Test",
            summary=EvidenceSummary(
                tests=5,
                failures=0,
                errors=0,
                time=3.0,
            ),
        )

    def test_disabled_ai_review_skips_review(self, disabled_ai_policy, passing_evidence):
        """禁用时跳过 AI 评审"""
        result = evaluate_gate_with_ai_review(passing_evidence, disabled_ai_policy)

        assert result.decision == GateDecision.PASS
        assert result.ai_review_result is None
        assert "ai_review" not in result.triggered_rules


class TestEvaluateGateWithAIReviewEnabled:
    """测试 AI 评审启用时的门禁评估"""

    @pytest.fixture
    def enabled_ai_policy(self):
        """AI 评审启用的策略"""
        return PolicyConfig(
            ai_review=AIReviewPolicy(
                enabled=True,
                models=[
                    AIReviewModelConfig(name="gpt-4", provider="openai"),
                    AIReviewModelConfig(name="claude-3", provider="anthropic"),
                ],
                strategy="majority_vote",
                thresholds=AIReviewThresholds(pass_confidence=0.8, hitl_confidence=0.5),
            )
        )

    @pytest.fixture
    def passing_evidence(self):
        """测试通过的 Evidence"""
        return Evidence(
            run_id=_run_id(),
            input_nl="Test passing scenario",
            summary=EvidenceSummary(
                tests=5,
                failures=0,
                errors=0,
                time=3.0,
            ),
        )

    def test_enabled_ai_review_adds_result(self, enabled_ai_policy, passing_evidence):
        """启用时添加 AI 评审结果"""
        result = evaluate_gate_with_ai_review(passing_evidence, enabled_ai_policy)

        assert result.ai_review_result is not None
        assert "ai_review" in result.ai_review_result or "verdict" in result.ai_review_result

    def test_ai_review_result_structure(self, enabled_ai_policy, passing_evidence):
        """AI 评审结果结构正确"""
        result = evaluate_gate_with_ai_review(passing_evidence, enabled_ai_policy)

        ai_result = result.ai_review_result
        assert ai_result is not None
        assert "verdict" in ai_result
        assert "confidence" in ai_result
        assert "reasoning" in ai_result
        assert "model_votes" in ai_result


class TestAIReviewDecisionImpact:
    """测试 AI 评审对决策的影响"""

    def create_policy_with_thresholds(self, pass_confidence, hitl_confidence):
        """创建带阈值的策略"""
        return PolicyConfig(
            ai_review=AIReviewPolicy(
                enabled=True,
                models=[
                    AIReviewModelConfig(name="gpt-4", provider="openai"),
                ],
                strategy="majority_vote",
                thresholds=AIReviewThresholds(
                    pass_confidence=pass_confidence,
                    hitl_confidence=hitl_confidence,
                ),
            )
        )

    def test_passing_evidence_with_ai_review(self):
        """通过的证据 + AI 评审"""
        policy = self.create_policy_with_thresholds(0.8, 0.5)
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Run all tests",
            summary=EvidenceSummary(tests=10, failures=0, errors=0, time=5.0),
        )

        result = evaluate_gate_with_ai_review(evidence, policy)

        # 标准评估是 PASS，AI 评审可能保持或改变决策
        assert result.decision in [GateDecision.PASS, GateDecision.NEED_HITL, GateDecision.FAIL]
        assert result.ai_review_result is not None

    def test_high_risk_with_ai_review(self):
        """高危关键词 + AI 评审（高危优先或 AI 评审参与）"""
        policy = self.create_policy_with_thresholds(0.8, 0.5)
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="delete all production data",  # 高危
        )

        result = evaluate_gate_with_ai_review(evidence, policy)

        # 高危关键词或 AI 评审应触发 NEED_HITL 或 FAIL
        assert result.decision in [GateDecision.NEED_HITL, GateDecision.FAIL]
        # AI 评审结果也应存在
        assert result.ai_review_result is not None

    def test_failing_tests_with_ai_review(self):
        """失败的测试 + AI 评审"""
        policy = self.create_policy_with_thresholds(0.8, 0.5)
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Test",
            summary=EvidenceSummary(tests=5, failures=2, errors=0, time=3.0),
        )

        result = evaluate_gate_with_ai_review(evidence, policy)

        # 标准评估是 FAIL，AI 评审可能保持或改为 NEED_HITL
        assert result.decision in [GateDecision.FAIL, GateDecision.NEED_HITL]


class TestAIReviewTriggeredRules:
    """测试 AI 评审触发的规则标签"""

    @pytest.fixture
    def enabled_ai_policy(self):
        """AI 评审启用的策略"""
        return PolicyConfig(
            ai_review=AIReviewPolicy(
                enabled=True,
                models=[
                    AIReviewModelConfig(name="gpt-4", provider="openai"),
                ],
                strategy="majority_vote",
                thresholds=AIReviewThresholds(pass_confidence=0.8, hitl_confidence=0.5),
            )
        )

    def test_ai_review_passed_rule(self, enabled_ai_policy):
        """AI 评审通过的规则标签"""
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Test",
            summary=EvidenceSummary(tests=5, failures=0, errors=0, time=3.0),
        )

        result = evaluate_gate_with_ai_review(evidence, enabled_ai_policy)

        # 检查是否添加了 AI 评审相关规则
        ai_rules = [r for r in result.triggered_rules if r.startswith("ai_review")]
        assert len(ai_rules) > 0


class TestAIReviewErrorHandling:
    """测试 AI 评审错误处理"""

    def test_invalid_model_config_fallback(self):
        """无效模型配置回退到标准门禁"""
        # 空模型列表会导致 AI 评审失败
        policy = PolicyConfig(
            ai_review=AIReviewPolicy(
                enabled=True,
                models=[],  # 空模型列表
            )
        )
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Test",
            summary=EvidenceSummary(tests=5, failures=0, errors=0, time=3.0),
        )

        result = evaluate_gate_with_ai_review(evidence, policy)

        # 应回退到标准门禁结果（PASS 或 NEED_HITL 取决于实现）
        assert result.decision in [GateDecision.PASS, GateDecision.NEED_HITL]
        # AI 评审相关的规则应被记录（可能是 error 或 triggered_hitl）
        ai_rules = [r for r in result.triggered_rules if r.startswith("ai_review")]
        assert len(ai_rules) > 0


class TestIntegrationWithStandardGate:
    """测试与标准门禁的集成"""

    def test_standard_gate_unchanged(self):
        """标准门禁评估不受影响"""
        policy = PolicyConfig(ai_review=AIReviewPolicy(enabled=False))
        evidence = Evidence(
            run_id=_run_id(),
            input_nl="Test",
            summary=EvidenceSummary(tests=5, failures=0, errors=0, time=3.0),
        )

        # 两种方式应返回相同结果
        standard_result = evaluate_gate(evidence, policy)
        ai_result = evaluate_gate_with_ai_review(evidence, policy)

        assert standard_result.decision == ai_result.decision
        assert standard_result.reason == ai_result.reason
