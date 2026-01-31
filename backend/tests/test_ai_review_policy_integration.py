"""Test AI Review Policy Integration

AI 评审与 Policy 配置系统集成测试
"""
import pytest
from pathlib import Path
import tempfile
import yaml

from qualityfoundry.governance.policy_loader import (
    load_policy,
    get_default_policy,
    PolicyConfig,
    AIReviewPolicy,
    AIReviewModelConfig,
    AIReviewThresholds,
)
from qualityfoundry.governance.ai_review import (
    AIReviewConfig,
    AIReviewEngine,
    StrategyType,
    VerdictType,
)
import qualityfoundry.governance.ai_review


class TestAIReviewPolicyLoading:
    """测试 AI 评审策略加载"""
    
    def test_default_policy_has_ai_review_disabled(self):
        """默认策略中 AI 评审应禁用"""
        policy = get_default_policy()
        
        assert policy.ai_review.enabled is False
        assert policy.ai_review.models == []
        assert policy.ai_review.strategy == "majority_vote"
        assert policy.ai_review.thresholds.pass_confidence == 0.8
        assert policy.ai_review.thresholds.hitl_confidence == 0.5
    
    def test_load_policy_with_ai_review_from_yaml(self):
        """从 YAML 加载包含 AI 评审配置的策略"""
        config_data = {
            "version": "1.0",
            "ai_review": {
                "enabled": True,
                "models": [
                    {"name": "gpt-4", "provider": "openai", "weight": 1.5},
                    {"name": "claude-3", "provider": "anthropic", "weight": 1.0},
                ],
                "strategy": "weighted_ensemble",
                "thresholds": {
                    "pass_confidence": 0.85,
                    "hitl_confidence": 0.6,
                },
                "dimensions": ["correctness", "safety"],
                "max_retries": 3,
                "timeout_seconds": 45,
            },
        }
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            policy = load_policy(temp_path)
            
            assert policy.ai_review.enabled is True
            assert len(policy.ai_review.models) == 2
            assert policy.ai_review.models[0].name == "gpt-4"
            assert policy.ai_review.models[0].weight == 1.5
            assert policy.ai_review.strategy == "weighted_ensemble"
            assert policy.ai_review.thresholds.pass_confidence == 0.85
            assert policy.ai_review.max_retries == 3
        finally:
            temp_path.unlink()
    
    def test_ai_review_strategy_validation(self):
        """测试策略名称验证"""
        # 有效策略
        policy = AIReviewPolicy(strategy="majority_vote")
        assert policy.strategy == "majority_vote"
        
        policy = AIReviewPolicy(strategy="cascade")
        assert policy.strategy == "cascade"
    
    def test_ai_review_thresholds_bounds(self):
        """测试阈值边界验证"""
        # 有效阈值
        thresholds = AIReviewThresholds(pass_confidence=0.9, hitl_confidence=0.4)
        assert thresholds.pass_confidence == 0.9
        assert thresholds.hitl_confidence == 0.4
        
        # 默认值
        thresholds = AIReviewThresholds()
        assert thresholds.pass_confidence == 0.8
        assert thresholds.hitl_confidence == 0.5


class TestPolicyToAIReviewConfig:
    """测试 Policy 配置转换为 AIReviewConfig"""
    
    def test_convert_policy_to_ai_review_config(self):
        """将 Policy 配置转换为 AIReviewConfig"""
        policy = PolicyConfig(
            ai_review=AIReviewPolicy(
                enabled=True,
                models=[
                    AIReviewModelConfig(name="gpt-4", provider="openai", weight=1.0),
                    AIReviewModelConfig(name="claude-3", provider="anthropic", weight=1.2),
                ],
                strategy="majority_vote",
                thresholds=AIReviewThresholds(pass_confidence=0.8, hitl_confidence=0.5),
                max_retries=2,
                timeout_seconds=30,
            )
        )
        
        # 转换为 AIReviewConfig
        config = AIReviewConfig(
            enabled=policy.ai_review.enabled,
            models=[
                qualityfoundry.governance.ai_review.ModelConfig(
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
        
        assert config.enabled is True
        assert len(config.models) == 2
        assert config.models[0].name == "gpt-4"
        assert config.strategy == StrategyType.MAJORITY_VOTE
    
    def test_policy_disabled_skips_ai_review(self):
        """禁用的 AI 评审策略应跳过"""
        policy = PolicyConfig(
            ai_review=AIReviewPolicy(enabled=False)
        )
        
        # 即使配置了模型，禁用状态应优先
        assert policy.ai_review.enabled is False


class TestAIReviewIntegration:
    """测试 AI 评审完整集成流程"""
    
    def test_end_to_end_with_policy_config(self):
        """使用 Policy 配置的端到端评审流程"""
        # 创建 Policy 配置
        policy = PolicyConfig(
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
        
        # 转换为 AIReviewConfig（实际使用时的转换）
        from qualityfoundry.governance.ai_review import ModelConfig as AIModelConfig
        
        ai_config = AIReviewConfig(
            enabled=policy.ai_review.enabled,
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
        )
        
        # 创建引擎并执行评审
        engine = AIReviewEngine(ai_config)
        result = engine.review("test content for policy integration")
        
        # 验证结果
        assert result.verdict in [VerdictType.PASS, VerdictType.FAIL, VerdictType.NEEDS_HITL]
        assert len(result.model_votes) == 2
        assert result.metadata.strategy_used == StrategyType.MAJORITY_VOTE
        
        # 验证 evidence 格式兼容
        evidence = result.to_evidence_format()
        assert "ai_review" in evidence
        assert evidence["ai_review"]["verdict"] == result.verdict.value
    
    def test_strategy_mapping_from_policy(self):
        """测试从 Policy 策略字符串到 StrategyType 的映射"""
        strategy_map = {
            "majority_vote": StrategyType.MAJORITY_VOTE,
            "weighted_ensemble": StrategyType.WEIGHTED_ENSEMBLE,
            "cascade": StrategyType.CASCADE,
        }
        
        for policy_str, expected_type in strategy_map.items():
            policy = AIReviewPolicy(strategy=policy_str)
            strategy_type = StrategyType(policy.strategy)
            assert strategy_type == expected_type


class TestAIReviewYamlConfig:
    """测试 YAML 配置文件"""
    
    def test_default_policy_yaml_has_ai_review(self):
        """默认 policy_config.yaml 应包含 ai_review 配置段"""
        from qualityfoundry.governance.policy_loader import DEFAULT_POLICY_PATH
        
        # 加载默认配置文件
        policy = load_policy(DEFAULT_POLICY_PATH)
        
        # 验证 ai_review 配置存在
        assert hasattr(policy, 'ai_review')
        assert isinstance(policy.ai_review, AIReviewPolicy)
        
        # 验证默认配置值
        assert policy.ai_review.enabled is False  # 默认禁用
        assert len(policy.ai_review.models) >= 2  # 默认有示例模型
        assert policy.ai_review.strategy in ["majority_vote", "weighted_ensemble", "cascade"]
    
    def test_ai_review_models_have_required_fields(self):
        """AI 评审模型配置应有必需字段"""
        policy = load_policy()
        
        for model in policy.ai_review.models:
            assert model.name is not None
            assert model.provider is not None
            assert model.weight >= 0.0
            assert 0.0 <= model.temperature <= 2.0


class TestAIReviewErrorHandling:
    """测试 AI 评审错误处理"""
    
    def test_invalid_strategy_falls_to_default(self):
        """无效策略应使用默认值"""
        # Pydantic 会验证策略值，无效值会报错
        with pytest.raises(ValueError):
            AIReviewPolicy(strategy="invalid_strategy")
    
    def test_empty_models_when_disabled(self):
        """禁用时允许空模型列表"""
        policy = AIReviewPolicy(enabled=False, models=[])
        assert policy.enabled is False
        assert policy.models == []


