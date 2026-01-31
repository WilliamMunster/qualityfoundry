"""QualityFoundry - AI Review Models

AI 评审数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class VerdictType(str, Enum):
    """评审裁决类型"""
    PASS = "PASS"
    NEEDS_HITL = "NEEDS_HITL"  # 需要人工介入
    FAIL = "FAIL"


class StrategyType(str, Enum):
    """多模型评审策略"""
    MAJORITY_VOTE = "majority_vote"  # 多数投票
    WEIGHTED_ENSEMBLE = "weighted_ensemble"  # 加权投票
    CASCADE = "cascade"  # 级联评审


class ModelConfig(BaseModel):
    """单个模型配置"""
    name: str = Field(..., description="模型名称，如 gpt-4, claude-3-sonnet")
    provider: str = Field(..., description="提供商: openai, anthropic, deepseek, local")
    weight: float = Field(1.0, description="加权投票时的权重")
    temperature: float = Field(0.0, description="温度参数，0=确定性")
    api_key: Optional[str] = Field(None, description="API Key（可选，如使用全局配置）")
    base_url: Optional[str] = Field(None, description="自定义 Base URL")
    model_id: Optional[UUID] = Field(None, description="关联的 ai_configs 表 ID")


class AIReviewConfig(BaseModel):
    """AI 评审配置"""
    enabled: bool = Field(False, description="是否启用 AI 评审")
    models: List[ModelConfig] = Field(default_factory=list, description="多模型配置")
    strategy: StrategyType = Field(StrategyType.MAJORITY_VOTE, description="评审策略")
    hitl_threshold: float = Field(0.7, ge=0.0, le=1.0, description="低于此置信度触发人工")
    pass_threshold: float = Field(0.8, ge=0.0, le=1.0, description="通过的置信度阈值")
    dimensions: List[str] = Field(
        default_factory=lambda: ["correctness"],
        description="评审维度: correctness, safety, clarity, completeness"
    )
    max_retries: int = Field(2, ge=0, description="单个模型最大重试次数")
    timeout_seconds: int = Field(30, ge=1, description="单次评审超时时间")


class ModelVote(BaseModel):
    """单个模型的投票结果"""
    model_name: str
    provider: str
    verdict: VerdictType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    raw_response: Optional[str] = None
    duration_ms: Optional[int] = None


class AIMetadata(BaseModel):
    """AI 评审元数据（用于审计）"""
    review_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prompt_hash: Optional[str] = None  # SHA256 of the prompt
    model_versions: Dict[str, str] = Field(default_factory=dict)
    strategy_used: StrategyType
    total_duration_ms: Optional[int] = None


class AIReviewResult(BaseModel):
    """AI 评审结果"""
    verdict: VerdictType
    confidence: float = Field(ge=0.0, le=1.0)
    model_votes: List[ModelVote] = Field(default_factory=list)
    reasoning: str
    metadata: AIMetadata
    
    # 扩展字段 - 用于 evidence.json 集成
    hitl_triggered: bool = False
    hitl_reason: Optional[str] = None

    def to_evidence_format(self) -> Dict[str, Any]:
        """转换为 evidence.json 兼容格式"""
        return {
            "ai_review": {
                "verdict": self.verdict.value,
                "confidence": self.confidence,
                "reasoning": self.reasoning,
                "hitl_triggered": self.hitl_triggered,
                "metadata": {
                    "review_id": str(self.metadata.review_id),
                    "timestamp": self.metadata.timestamp.isoformat(),
                    "prompt_hash": self.metadata.prompt_hash,
                    "strategy": self.metadata.strategy_used.value,
                    "total_duration_ms": self.metadata.total_duration_ms,
                },
                "model_votes": [
                    {
                        "model": v.model_name,
                        "provider": v.provider,
                        "verdict": v.verdict.value,
                        "confidence": v.confidence,
                        "reasoning": v.reasoning,
                        "duration_ms": v.duration_ms,
                    }
                    for v in self.model_votes
                ],
            }
        }
