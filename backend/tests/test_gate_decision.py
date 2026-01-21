"""Tests for Gate Decision (PR-3)

验证门禁决策逻辑的正确性。
"""


from qualityfoundry.governance.gate import (
    GateDecision,
    GateResult,
    evaluate_gate,
    evaluate_gate_with_hitl,
    _check_high_risk,
)
from qualityfoundry.governance.policy_loader import get_default_policy
from qualityfoundry.governance.tracing.collector import (
    Evidence,
    EvidenceSummary,
    ToolCallSummary,
)


class TestHighRiskKeywordDetection:
    """高危关键词检测测试"""

    def test_detect_production(self):
        """检测 production 关键词"""
        result = _check_high_risk("deploy to production server")
        assert result == "production"

    def test_detect_prod(self):
        """检测 prod 关键词"""
        result = _check_high_risk("push to prod environment")
        assert result == "prod"

    def test_detect_delete(self):
        """检测 delete 关键词"""
        result = _check_high_risk("delete all test data")
        assert result == "delete"

    def test_detect_drop_table_pattern(self):
        """检测 drop table 模式"""
        result = _check_high_risk("execute drop table users")
        # drop 是关键词，所以会被检测到
        assert result == "drop"

    def test_detect_rm_rf_pattern(self):
        """检测 rm -rf 模式"""
        result = _check_high_risk("run rm -rf /tmp/test")
        # remove 是关键词
        assert result == "remove" or "pattern:" in result

    def test_detect_sudo_pattern(self):
        """检测 sudo 模式"""
        result = _check_high_risk("use sudo apt install")
        assert result is not None
        assert "sudo" in result or "pattern:" in result

    def test_no_high_risk_normal_input(self):
        """普通输入不触发高危检测"""
        result = _check_high_risk("run unit tests for login feature")
        assert result is None

    def test_case_insensitive(self):
        """大小写不敏感"""
        result = _check_high_risk("Deploy to PRODUCTION")
        assert result == "production"

    def test_priority_keywords(self):
        """优先返回更重要的关键词"""
        # production 优先级高于 delete
        result = _check_high_risk("delete data in production")
        assert result == "production"


class TestGateDecisionWithJUnit:
    """基于 JUnit 结果的门禁决策测试"""

    def test_all_tests_passed(self):
        """所有测试通过 → PASS"""
        evidence = Evidence(
            run_id="test-run-1",
            input_nl="run all tests",
            summary=EvidenceSummary(
                tests=10,
                failures=0,
                errors=0,
                skipped=0,
                passed=10,
                time=1.5,
            ),
        )

        result = evaluate_gate(evidence)

        assert result.decision == GateDecision.PASS
        assert "10 tests passed" in result.reason
        assert "junit_all_passed" in result.triggered_rules

    def test_some_tests_failed(self):
        """有测试失败 → FAIL"""
        evidence = Evidence(
            run_id="test-run-2",
            input_nl="run tests",
            summary=EvidenceSummary(
                tests=10,
                failures=2,
                errors=0,
                skipped=1,
                passed=7,
                time=2.0,
            ),
        )

        result = evaluate_gate(evidence)

        assert result.decision == GateDecision.FAIL
        assert "2 test(s) failed" in result.reason
        assert "junit_has_failures" in result.triggered_rules

    def test_tests_with_errors(self):
        """有错误 → FAIL"""
        evidence = Evidence(
            run_id="test-run-3",
            input_nl="run tests",
            summary=EvidenceSummary(
                tests=5,
                failures=0,
                errors=1,
                skipped=0,
                passed=4,
                time=1.0,
            ),
        )

        result = evaluate_gate(evidence)

        assert result.decision == GateDecision.FAIL
        assert "1 test(s) failed" in result.reason

    def test_evidence_summary_included(self):
        """结果包含 evidence_summary"""
        evidence = Evidence(
            run_id="test-run-4",
            input_nl="run tests",
            summary=EvidenceSummary(tests=5, failures=0, errors=0, skipped=0, passed=5),
        )

        result = evaluate_gate(evidence)

        assert result.evidence_summary is not None
        assert result.evidence_summary["tests"] == 5


class TestGateDecisionWithToolCalls:
    """基于 ToolCall 状态的门禁决策测试（无 JUnit 时）"""

    def test_all_tools_succeeded(self):
        """所有工具执行成功 → PASS"""
        evidence = Evidence(
            run_id="test-run-5",
            input_nl="run tests",
            tool_calls=[
                ToolCallSummary(tool_name="run_pytest", status="success"),
                ToolCallSummary(tool_name="run_playwright", status="success"),
            ],
        )

        result = evaluate_gate(evidence)

        assert result.decision == GateDecision.PASS
        assert "All tool executions succeeded" in result.reason
        assert "all_tools_succeeded" in result.triggered_rules

    def test_some_tools_failed(self):
        """有工具执行失败 → FAIL"""
        evidence = Evidence(
            run_id="test-run-6",
            input_nl="run tests",
            tool_calls=[
                ToolCallSummary(tool_name="run_pytest", status="success"),
                ToolCallSummary(tool_name="run_playwright", status="failed"),
            ],
        )

        result = evaluate_gate(evidence)

        assert result.decision == GateDecision.FAIL
        assert "run_playwright" in result.reason
        assert "tool_execution_failed" in result.triggered_rules

    def test_no_execution_data(self):
        """无执行数据 → FAIL"""
        evidence = Evidence(
            run_id="test-run-7",
            input_nl="run tests",
        )

        result = evaluate_gate(evidence)

        assert result.decision == GateDecision.FAIL
        assert "No execution data" in result.reason
        assert "no_execution_data" in result.triggered_rules


class TestGateDecisionWithHITL:
    """HITL（人工审核）触发测试"""

    def test_high_risk_triggers_hitl(self):
        """高危关键词触发 NEED_HITL"""
        evidence = Evidence(
            run_id="test-run-8",
            input_nl="delete all data in production database",
            summary=EvidenceSummary(tests=5, failures=0, errors=0, skipped=0, passed=5),
        )

        result = evaluate_gate(evidence)

        assert result.decision == GateDecision.NEED_HITL
        assert "High-risk keyword" in result.reason
        assert any("high_risk_keyword" in r for r in result.triggered_rules)

    def test_hitl_priority_over_pass(self):
        """HITL 优先级高于 PASS（即使测试全部通过）"""
        evidence = Evidence(
            run_id="test-run-9",
            input_nl="run tests for production deployment",
            summary=EvidenceSummary(tests=10, failures=0, errors=0, skipped=0, passed=10),
        )

        result = evaluate_gate(evidence)

        # 即使所有测试通过，但包含高危关键词，仍然需要 HITL
        assert result.decision == GateDecision.NEED_HITL

    def test_evaluate_gate_with_hitl_creates_approval(self):
        """evaluate_gate_with_hitl 创建审批记录"""
        evidence = Evidence(
            run_id="test-run-10",
            input_nl="deploy to production",
        )

        result = evaluate_gate_with_hitl(evidence)

        assert result.decision == GateDecision.NEED_HITL
        assert result.approval_id is not None

    def test_evaluate_gate_with_hitl_no_approval_for_pass(self):
        """PASS 结果不创建审批记录"""
        evidence = Evidence(
            run_id="test-run-11",
            input_nl="run unit tests",
            summary=EvidenceSummary(tests=5, failures=0, errors=0, skipped=0, passed=5),
        )

        result = evaluate_gate_with_hitl(evidence)

        assert result.decision == GateDecision.PASS
        assert result.approval_id is None


class TestGateResultProperties:
    """GateResult 属性测试"""

    def test_passed_property(self):
        """passed 属性"""
        result = GateResult(decision=GateDecision.PASS, reason="All tests passed")
        assert result.passed is True

        result = GateResult(decision=GateDecision.FAIL, reason="Tests failed")
        assert result.passed is False

    def test_needs_approval_property(self):
        """needs_approval 属性"""
        result = GateResult(decision=GateDecision.NEED_HITL, reason="High risk")
        assert result.needs_approval is True

        result = GateResult(decision=GateDecision.PASS, reason="OK")
        assert result.needs_approval is False


class TestHighRiskKeywordsSet:
    """高危关键词集合测试（使用 Policy Config）"""

    def test_contains_critical_keywords(self):
        """默认策略包含关键高危词"""
        policy = get_default_policy()
        high_risk_keywords = set(policy.high_risk_keywords)
        critical = ["delete", "drop", "truncate", "production", "prod"]
        for keyword in critical:
            assert keyword in high_risk_keywords

    def test_keywords_is_list(self):
        """关键词是列表类型"""
        policy = get_default_policy()
        assert isinstance(policy.high_risk_keywords, list)
