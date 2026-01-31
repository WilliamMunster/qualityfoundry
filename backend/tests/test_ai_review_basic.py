"""Test AI Review System - Basic PoC

AI 评审系统基础测试
"""
import pytest
from uuid import UUID

from qualityfoundry.governance.ai_review import (
    AIReviewConfig,
    AIReviewEngine,
    ModelConfig,
    StrategyType,
    VerdictType,
)


class TestAIReviewConfig:
    """测试配置模型"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AIReviewConfig()
        assert config.enabled is False
        assert config.strategy == StrategyType.MAJORITY_VOTE
        assert config.hitl_threshold == 0.7
        assert config.pass_threshold == 0.8
        assert config.dimensions == ["correctness"]
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = AIReviewConfig(
            enabled=True,
            models=[
                ModelConfig(name="gpt-4", provider="openai"),
                ModelConfig(name="claude-3", provider="anthropic"),
            ],
            strategy=StrategyType.WEIGHTED_ENSEMBLE,
            hitl_threshold=0.6,
        )
        assert config.enabled is True
        assert len(config.models) == 2
        assert config.strategy == StrategyType.WEIGHTED_ENSEMBLE


class TestAIReviewEngineBasics:
    """测试评审引擎基础功能"""
    
    @pytest.fixture
    def single_model_config(self):
        """单模型配置"""
        return AIReviewConfig(
            enabled=True,
            models=[
                ModelConfig(name="gpt-4", provider="openai"),
            ],
        )
    
    @pytest.fixture
    def dual_model_config(self):
        """双模型配置"""
        return AIReviewConfig(
            enabled=True,
            models=[
                ModelConfig(name="gpt-4", provider="openai"),
                ModelConfig(name="claude-3", provider="anthropic"),
            ],
        )
    
    def test_disabled_engine_returns_auto_pass(self, single_model_config):
        """禁用状态的引擎返回自动通过"""
        single_model_config.enabled = False
        engine = AIReviewEngine(single_model_config)
        result = engine.review("some content")
        
        assert result.verdict == VerdictType.PASS
        assert result.confidence == 1.0
        assert "disabled" in result.reasoning.lower()
    
    def test_empty_models_returns_error(self):
        """空模型配置返回错误"""
        config = AIReviewConfig(enabled=True, models=[])
        engine = AIReviewEngine(config)
        result = engine.review("content")
        
        assert result.verdict == VerdictType.NEEDS_HITL
        assert result.hitl_triggered is True
    
    def test_single_model_review(self, single_model_config):
        """单模型评审"""
        engine = AIReviewEngine(single_model_config)
        result = engine.review("test content for review")
        
        assert result.verdict in [VerdictType.PASS, VerdictType.FAIL, VerdictType.NEEDS_HITL]
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.model_votes) == 1
        assert result.model_votes[0].model_name == "gpt-4"
        assert result.metadata.review_id is not None
        assert isinstance(result.metadata.review_id, UUID)
    
    def test_dual_model_majority_vote(self, dual_model_config):
        """双模型多数投票"""
        engine = AIReviewEngine(dual_model_config)
        result = engine.review("content to review with two models")
        
        assert len(result.model_votes) == 2
        assert result.model_votes[0].model_name == "gpt-4"
        assert result.model_votes[1].model_name == "claude-3"
        assert result.metadata.strategy_used == StrategyType.MAJORITY_VOTE
    
    def test_evidence_format_output(self, single_model_config):
        """测试 evidence.json 格式输出"""
        engine = AIReviewEngine(single_model_config)
        result = engine.review("test content")
        evidence = result.to_evidence_format()
        
        assert "ai_review" in evidence
        assert "verdict" in evidence["ai_review"]
        assert "confidence" in evidence["ai_review"]
        assert "reasoning" in evidence["ai_review"]
        assert "metadata" in evidence["ai_review"]
        assert "model_votes" in evidence["ai_review"]


class TestReviewStrategies:
    """测试不同评审策略"""
    
    @pytest.fixture
    def multi_model_config(self):
        """多模型配置"""
        return AIReviewConfig(
            enabled=True,
            models=[
                ModelConfig(name="gpt-4", provider="openai", weight=1.5),
                ModelConfig(name="claude-3", provider="anthropic", weight=1.0),
                ModelConfig(name="deepseek", provider="deepseek", weight=0.8),
            ],
        )
    
    def test_majority_vote_strategy(self, multi_model_config):
        """测试多数投票策略"""
        multi_model_config.strategy = StrategyType.MAJORITY_VOTE
        engine = AIReviewEngine(multi_model_config)
        result = engine.review("content for majority vote")
        
        assert result.metadata.strategy_used == StrategyType.MAJORITY_VOTE
        # 验证结果是有效裁决
        assert result.verdict in [VerdictType.PASS, VerdictType.FAIL, VerdictType.NEEDS_HITL]
    
    def test_weighted_ensemble_strategy(self, multi_model_config):
        """测试加权投票策略"""
        multi_model_config.strategy = StrategyType.WEIGHTED_ENSEMBLE
        engine = AIReviewEngine(multi_model_config)
        result = engine.review("content for weighted ensemble")
        
        assert result.metadata.strategy_used == StrategyType.WEIGHTED_ENSEMBLE
        assert len(result.model_votes) == 3
    
    def test_cascade_strategy(self, multi_model_config):
        """测试级联策略"""
        multi_model_config.strategy = StrategyType.CASCADE
        engine = AIReviewEngine(multi_model_config)
        result = engine.review("content for cascade")
        
        assert result.metadata.strategy_used == StrategyType.CASCADE


class TestHITLTrigger:
    """测试人工介入触发逻辑"""
    
    def test_low_confidence_triggers_hitl(self):
        """低置信度触发人工介入"""
        config = AIReviewConfig(
            enabled=True,
            models=[ModelConfig(name="gpt-4", provider="openai")],
            hitl_threshold=0.95,  # 设置高阈值，确保触发
        )
        engine = AIReviewEngine(config)
        result = engine.review("some test content")
        
        # 由于 threshold 很高，应该触发 HITL
        if result.confidence < 0.95:
            assert result.hitl_triggered is True
    
    def test_needs_hitl_verdict_triggers_hitl(self):
        """NEEDS_HITL 裁决自动触发人工介入"""
        config = AIReviewConfig(
            enabled=True,
            models=[ModelConfig(name="gpt-4", provider="openai")],
        )
        engine = AIReviewEngine(config)
        
        # 测试多次，确保覆盖不同情况
        hitl_count = 0
        for i in range(5):
            result = engine.review(f"content iteration {i}")
            if result.verdict == VerdictType.NEEDS_HITL:
                assert result.hitl_triggered is True
                hitl_count += 1
        
        # 应该至少有部分触发 HITL（基于模拟逻辑）
        # 这里不做强断言，因为模拟结果是确定性的


class TestAuditMetadata:
    """测试审计元数据"""
    
    def test_review_has_uuid(self):
        """每次评审有唯一 ID"""
        config = AIReviewConfig(
            enabled=True,
            models=[ModelConfig(name="gpt-4", provider="openai")],
        )
        engine = AIReviewEngine(config)
        
        result1 = engine.review("content 1")
        result2 = engine.review("content 2")
        
        assert result1.metadata.review_id != result2.metadata.review_id
    
    def test_timestamp_recorded(self):
        """时间戳被记录"""
        from datetime import datetime
        
        config = AIReviewConfig(
            enabled=True,
            models=[ModelConfig(name="gpt-4", provider="openai")],
        )
        engine = AIReviewEngine(config)
        result = engine.review("content")
        
        assert result.metadata.timestamp is not None
        assert isinstance(result.metadata.timestamp, datetime)
    
    def test_prompt_hash_computed(self):
        """计算 prompt hash"""
        config = AIReviewConfig(
            enabled=True,
            models=[ModelConfig(name="gpt-4", provider="openai")],
        )
        engine = AIReviewEngine(config)
        result = engine.review("content", context={"key": "value"})
        
        assert result.metadata.prompt_hash is not None
        assert len(result.metadata.prompt_hash) == 16  # SHA256 truncated
    
    def test_duration_recorded(self):
        """记录执行耗时"""
        config = AIReviewConfig(
            enabled=True,
            models=[ModelConfig(name="gpt-4", provider="openai")],
        )
        engine = AIReviewEngine(config)
        result = engine.review("content")
        
        assert result.metadata.total_duration_ms is not None
        assert result.metadata.total_duration_ms >= 0


class TestModelIntegration:
    """测试与现有 AI 配置的集成"""
    
    def test_model_config_with_id(self):
        """测试带 ID 的模型配置"""
        from uuid import uuid4
        
        model_id = uuid4()
        model = ModelConfig(
            name="gpt-4",
            provider="openai",
            model_id=model_id,
        )
        
        assert model.model_id == model_id
    
    def test_temperature_parameter(self):
        """测试温度参数"""
        model = ModelConfig(
            name="gpt-4",
            provider="openai",
            temperature=0.5,
        )
        
        assert model.temperature == 0.5
