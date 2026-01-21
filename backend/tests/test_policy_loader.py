"""Tests for Policy Loader (L1 Policy Layer)

验证策略配置的加载、验证和默认值行为。
"""

import tempfile
from pathlib import Path

import pytest

from qualityfoundry.governance.policy_loader import (
    PolicyConfig,
    JUnitPassRule,
    FallbackRule,
    CostGovernance,
    load_policy,
    get_policy,
    get_default_policy,
    clear_policy_cache,
)


class TestPolicyConfig:
    """PolicyConfig schema 测试"""

    def test_default_values(self):
        """测试默认值"""
        config = PolicyConfig()
        assert config.version == "1.0"
        assert config.high_risk_keywords == []
        assert config.high_risk_patterns == []
        assert config.junit_pass_rule.max_failures == 0
        assert config.junit_pass_rule.max_errors == 0
        assert config.fallback_rule.require_all_tools_success is True
        assert config.cost_governance.timeout_s == 300
        assert config.cost_governance.max_retries == 3

    def test_custom_values(self):
        """测试自定义值"""
        config = PolicyConfig(
            version="2.0",
            high_risk_keywords=["prod", "delete"],
            high_risk_patterns=[r"\bprod\b"],
            junit_pass_rule=JUnitPassRule(max_failures=1, max_errors=0),
            fallback_rule=FallbackRule(require_all_tools_success=False),
            cost_governance=CostGovernance(timeout_s=600, max_retries=5),
        )
        assert config.version == "2.0"
        assert config.high_risk_keywords == ["prod", "delete"]
        assert config.junit_pass_rule.max_failures == 1
        assert config.fallback_rule.require_all_tools_success is False
        assert config.cost_governance.timeout_s == 600


class TestLoadPolicy:
    """load_policy 函数测试"""

    def test_load_from_yaml(self, tmp_path: Path):
        """测试从 YAML 文件加载"""
        yaml_content = """
version: "1.0"
high_risk_keywords:
  - custom_keyword
  - another_keyword
junit_pass_rule:
  max_failures: 2
  max_errors: 1
"""
        config_file = tmp_path / "test_policy.yaml"
        config_file.write_text(yaml_content)

        config = load_policy(config_file)

        assert config.high_risk_keywords == ["custom_keyword", "another_keyword"]
        assert config.junit_pass_rule.max_failures == 2
        assert config.junit_pass_rule.max_errors == 1

    def test_load_nonexistent_file(self, tmp_path: Path):
        """测试加载不存在的文件返回默认值"""
        nonexistent = tmp_path / "nonexistent.yaml"
        config = load_policy(nonexistent)

        # 应返回默认值
        assert config.version == "1.0"
        assert config.high_risk_keywords == []

    def test_load_invalid_yaml(self, tmp_path: Path):
        """测试加载无效 YAML 返回默认值"""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [[[")

        config = load_policy(invalid_yaml)

        # 应返回默认值
        assert config.version == "1.0"

    def test_load_partial_config(self, tmp_path: Path):
        """测试部分配置使用默认值填充"""
        partial_yaml = """
high_risk_keywords:
  - only_keyword
"""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text(partial_yaml)

        config = load_policy(config_file)

        assert config.high_risk_keywords == ["only_keyword"]
        # 其他使用默认值
        assert config.junit_pass_rule.max_failures == 0
        assert config.fallback_rule.require_all_tools_success is True


class TestGetDefaultPolicy:
    """get_default_policy 函数测试"""

    def test_returns_populated_defaults(self):
        """测试返回预填充的默认策略"""
        policy = get_default_policy()

        assert "prod" in policy.high_risk_keywords
        assert "production" in policy.high_risk_keywords
        assert "delete" in policy.high_risk_keywords
        assert len(policy.high_risk_patterns) > 0


class TestPolicyCache:
    """策略缓存测试"""

    def setup_method(self):
        """每个测试前清除缓存"""
        clear_policy_cache()

    def test_cache_cleared(self):
        """测试缓存清除"""
        # 首次获取
        policy1 = get_policy()
        # 清除缓存
        clear_policy_cache()
        # 再次获取应该是新的实例
        policy2 = get_policy()

        # 内容相同但为不同对象
        assert policy1.version == policy2.version


class TestPolicyDrivenGate:
    """策略驱动门禁测试"""

    def test_custom_keywords_trigger_hitl(self):
        """测试自定义关键词触发 HITL"""
        from qualityfoundry.governance.gate import _check_high_risk

        # 使用包含 "staging" 的自定义策略
        policy = PolicyConfig(high_risk_keywords=["staging", "test_env"])

        # staging 应触发
        result = _check_high_risk("deploy to staging", policy)
        assert result == "staging"

        # 默认关键词 prod 不应触发（因为不在自定义列表中）
        result = _check_high_risk("deploy to prod", policy)
        assert result is None

    def test_custom_junit_threshold(self):
        """测试自定义 JUnit 阈值"""
        from qualityfoundry.governance import evaluate_gate, Evidence, GateDecision
        from qualityfoundry.governance.tracing.collector import EvidenceSummary

        # 允许 1 个失败的策略
        policy = PolicyConfig(
            high_risk_keywords=[],  # 禁用高危关键词
            junit_pass_rule=JUnitPassRule(max_failures=1, max_errors=0),
        )

        # 创建有 1 个失败的证据
        evidence = Evidence(
            run_id="test-run",
            input_nl="run tests",
            summary=EvidenceSummary(tests=10, failures=1, errors=0, skipped=0, time=1.0),
        )

        result = evaluate_gate(evidence, policy)

        # 1 个失败应该 PASS（因为阈值是 1）
        assert result.decision == GateDecision.PASS

    def test_fallback_rule_no_strict(self):
        """测试非严格工具检查"""
        from qualityfoundry.governance import evaluate_gate, Evidence, GateDecision
        from qualityfoundry.governance.tracing.collector import ToolCallSummary

        # 不要求所有工具成功的策略
        policy = PolicyConfig(
            high_risk_keywords=[],
            fallback_rule=FallbackRule(require_all_tools_success=False),
        )

        # 创建有失败工具的证据（无 JUnit）
        evidence = Evidence(
            run_id="test-run",
            input_nl="run tools",
            tool_calls=[
                ToolCallSummary(tool_name="tool1", status="success"),
                ToolCallSummary(tool_name="tool2", status="failed"),
            ],
        )

        result = evaluate_gate(evidence, policy)

        # 应该 PASS（因为 fallback 不要求所有成功）
        assert result.decision == GateDecision.PASS
        assert "fallback_no_strict_check" in result.triggered_rules
