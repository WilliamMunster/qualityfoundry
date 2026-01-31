"""QualityFoundry - AI Review Engine

AI 评审引擎核心实现
"""
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from collections import Counter

from .models import (
    AIReviewConfig,
    AIReviewResult,
    AIMetadata,
    ModelConfig,
    ModelVote,
    StrategyType,
    VerdictType,
)


class AIReviewEngine:
    """AI 评审引擎
    
    支持多模型评审，多种策略（多数投票、加权投票、级联）
    """
    
    def __init__(self, config: AIReviewConfig):
        self.config = config
    
    def review(
        self,
        content: str,
        context: Optional[Dict] = None,
        prompt_template: Optional[str] = None,
    ) -> AIReviewResult:
        """执行 AI 评审
        
        Args:
            content: 待评审内容
            context: 额外上下文（如代码语言、测试框架等）
            prompt_template: 自定义 prompt 模板
            
        Returns:
            AIReviewResult: 评审结果
        """
        if not self.config.enabled:
            return self._create_disabled_result()
        
        if not self.config.models:
            return self._create_error_result("No models configured")
        
        # 计算 prompt hash（用于审计）
        prompt_hash = self._compute_prompt_hash(content, context, prompt_template)
        
        # 收集各模型投票
        start_time = time.time()
        model_votes = []
        
        for model_config in self.config.models:
            vote = self._query_model(model_config, content, context, prompt_template)
            model_votes.append(vote)
        
        total_duration_ms = int((time.time() - start_time) * 1000)
        
        # 聚合投票结果
        verdict, confidence = self._aggregate_votes(model_votes)
        
        # 构建元数据
        metadata = AIMetadata(
            prompt_hash=prompt_hash,
            model_versions={m.name: "unknown" for m in self.config.models},
            strategy_used=self.config.strategy,
            total_duration_ms=total_duration_ms,
        )
        
        # 确定是否需要人工介入
        hitl_triggered = self._should_trigger_hitl(verdict, confidence)
        
        # 生成综合理由
        reasoning = self._generate_reasoning(model_votes, verdict)
        
        return AIReviewResult(
            verdict=verdict,
            confidence=confidence,
            model_votes=model_votes,
            reasoning=reasoning,
            metadata=metadata,
            hitl_triggered=hitl_triggered,
            hitl_reason="Low confidence" if hitl_triggered else None,
        )
    
    def _query_model(
        self,
        model_config: ModelConfig,
        content: str,
        context: Optional[Dict],
        prompt_template: Optional[str],
    ) -> ModelVote:
        """查询单个模型
        
        注意：当前为 PoC 实现，使用模拟响应。
        生产环境应调用实际 AI 服务。
        """
        start_time = time.time()
        
        # PoC: 模拟模型响应（实际应调用 AI 服务）
        # 基于内容哈希产生确定性响应，便于测试
        content_hash = hashlib.md5(content.encode()).hexdigest()
        hash_int = int(content_hash[:8], 16)
        
        # 模拟不同模型的倾向性
        model_bias = {
            "gpt-4": 0.1,
            "claude-3": 0.05,
            "deepseek": 0.0,
        }.get(model_config.name, 0.0)
        
        # 根据内容决定裁决（确定性模拟）
        score = (hash_int % 100) / 100.0 + model_bias
        
        if score > 0.7:
            verdict = VerdictType.PASS
            confidence = min(0.95, score)
            reasoning = f"Content appears valid (score: {score:.2f})"
        elif score > 0.4:
            verdict = VerdictType.NEEDS_HITL
            confidence = 0.6
            reasoning = f"Uncertain about content quality (score: {score:.2f})"
        else:
            verdict = VerdictType.FAIL
            confidence = min(0.95, 1.0 - score)
            reasoning = f"Content has potential issues (score: {score:.2f})"
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return ModelVote(
            model_name=model_config.name,
            provider=model_config.provider,
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            raw_response=f"Mock response for {model_config.name}",
            duration_ms=duration_ms,
        )
    
    def _aggregate_votes(self, votes: List[ModelVote]) -> Tuple[VerdictType, float]:
        """聚合多模型投票
        
        根据配置的 strategy 选择不同聚合方式
        """
        if self.config.strategy == StrategyType.MAJORITY_VOTE:
            return self._majority_vote(votes)
        elif self.config.strategy == StrategyType.WEIGHTED_ENSEMBLE:
            return self._weighted_ensemble(votes)
        elif self.config.strategy == StrategyType.CASCADE:
            return self._cascade_vote(votes)
        else:
            return self._majority_vote(votes)
    
    def _majority_vote(self, votes: List[ModelVote]) -> Tuple[VerdictType, float]:
        """多数投票策略"""
        if not votes:
            return VerdictType.NEEDS_HITL, 0.0
        
        verdict_counts = Counter(v.verdict for v in votes)
        most_common = verdict_counts.most_common(1)[0]
        majority_verdict = most_common[0]
        
        # 计算平均置信度
        relevant_votes = [v for v in votes if v.verdict == majority_verdict]
        avg_confidence = sum(v.confidence for v in relevant_votes) / len(relevant_votes)
        
        return majority_verdict, avg_confidence
    
    def _weighted_ensemble(self, votes: List[ModelVote]) -> Tuple[VerdictType, float]:
        """加权投票策略"""
        if not votes:
            return VerdictType.NEEDS_HITL, 0.0
        
        # 构建模型名称到权重的映射
        weights = {m.name: m.weight for m in self.config.models}
        
        # 计算加权分数
        score_map = {VerdictType.PASS: 1.0, VerdictType.NEEDS_HITL: 0.5, VerdictType.FAIL: 0.0}
        total_weight = 0.0
        weighted_score = 0.0
        
        for vote in votes:
            weight = weights.get(vote.model_name, 1.0)
            weighted_score += score_map[vote.verdict] * weight * vote.confidence
            total_weight += weight
        
        if total_weight == 0:
            return VerdictType.NEEDS_HITL, 0.0
        
        final_score = weighted_score / total_weight
        
        if final_score > 0.7:
            return VerdictType.PASS, final_score
        elif final_score < 0.3:
            return VerdictType.FAIL, 1.0 - final_score
        else:
            return VerdictType.NEEDS_HITL, 0.5 + abs(final_score - 0.5)
    
    def _cascade_vote(self, votes: List[ModelVote]) -> Tuple[VerdictType, float]:
        """级联策略：第一个高置信度模型决定结果"""
        sorted_votes = sorted(votes, key=lambda v: v.confidence, reverse=True)
        
        for vote in sorted_votes:
            if vote.confidence >= self.config.pass_threshold:
                return vote.verdict, vote.confidence
        
        # 如果没有高置信度结果，返回 NEEDS_HITL
        return VerdictType.NEEDS_HITL, 0.5
    
    def _should_trigger_hitl(self, verdict: VerdictType, confidence: float) -> bool:
        """判断是否需要触发人工介入"""
        if verdict == VerdictType.NEEDS_HITL:
            return True
        if confidence < self.config.hitl_threshold:
            return True
        return False
    
    def _generate_reasoning(self, votes: List[ModelVote], final_verdict: VerdictType) -> str:
        """生成综合理由"""
        vote_summary = ", ".join(
            f"{v.model_name}:{v.verdict.value}({v.confidence:.2f})"
            for v in votes
        )
        return f"Final: {final_verdict.value} | Votes: [{vote_summary}]"
    
    def _compute_prompt_hash(
        self,
        content: str,
        context: Optional[Dict],
        prompt_template: Optional[str],
    ) -> str:
        """计算 prompt 哈希（用于审计）"""
        data = f"{content}:{context}:{prompt_template}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _create_disabled_result(self) -> AIReviewResult:
        """创建禁用状态的结果"""
        return AIReviewResult(
            verdict=VerdictType.PASS,
            confidence=1.0,
            reasoning="AI Review disabled, auto-pass",
            metadata=AIMetadata(
                strategy_used=self.config.strategy,
            ),
        )
    
    def _create_error_result(self, error_message: str) -> AIReviewResult:
        """创建错误状态的结果"""
        return AIReviewResult(
            verdict=VerdictType.NEEDS_HITL,
            confidence=0.0,
            reasoning=f"Error: {error_message}",
            metadata=AIMetadata(
                strategy_used=self.config.strategy,
            ),
            hitl_triggered=True,
            hitl_reason=error_message,
        )
