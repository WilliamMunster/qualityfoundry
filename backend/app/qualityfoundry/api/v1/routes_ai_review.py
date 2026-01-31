"""QualityFoundry - AI Review Routes

AI 评审配置和结果 API
"""
from uuid import UUID
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qualityfoundry.governance.policy_loader import get_policy
from qualityfoundry.governance.tracing.collector import load_evidence

router = APIRouter(prefix="/ai-review", tags=["ai-review"])


class AIReviewConfigResponse(BaseModel):
    """AI 评审配置响应"""
    enabled: bool
    strategy: str
    models_count: int
    models: list[dict[str, Any]]
    thresholds: dict[str, float]
    dimensions: list[str]


class AIReviewResultResponse(BaseModel):
    """AI 评审结果响应"""
    run_id: str
    has_ai_review: bool
    ai_review: dict[str, Any] | None = None


@router.get("/config", response_model=AIReviewConfigResponse)
def get_ai_review_config():
    """获取当前 AI 评审配置
    
    返回当前策略中配置的 AI 评审设置，
    包括是否启用、评审策略、模型列表、阈值等。
    
    Returns:
        AIReviewConfigResponse: AI 评审配置信息
    """
    policy = get_policy()
    ai_config = policy.ai_review
    
    # 脱敏处理：只返回模型名称和提供商，不暴露 API key
    models = [
        {
            "name": m.name,
            "provider": m.provider,
            "weight": m.weight,
            "temperature": m.temperature,
        }
        for m in ai_config.models
    ]
    
    return AIReviewConfigResponse(
        enabled=ai_config.enabled,
        strategy=ai_config.strategy,
        models_count=len(ai_config.models),
        models=models,
        thresholds={
            "pass_confidence": ai_config.thresholds.pass_confidence,
            "hitl_confidence": ai_config.thresholds.hitl_confidence,
        },
        dimensions=ai_config.dimensions,
    )


@router.get("/runs/{run_id}", response_model=AIReviewResultResponse)
def get_run_ai_review(run_id: UUID):
    """获取特定 Run 的 AI 评审结果
    
    从 evidence.json 中读取指定 Run 的 AI 评审结果。
    
    Args:
        run_id: 运行 ID
        
    Returns:
        AIReviewResultResponse: AI 评审结果
        
    Raises:
        HTTPException 404: 如果 Run 不存在或无 AI 评审数据
    """
    # 加载 evidence
    evidence = load_evidence(run_id)
    
    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run {run_id} not found or evidence missing"
        )
    
    # 检查是否有 AI 评审结果
    has_ai_review = evidence.ai_review is not None
    
    return AIReviewResultResponse(
        run_id=str(run_id),
        has_ai_review=has_ai_review,
        ai_review=evidence.ai_review,
    )


@router.get("/health")
def ai_review_health_check():
    """AI 评审系统健康检查
    
    快速检查 AI 评审系统状态。
    
    Returns:
        健康状态信息
    """
    policy = get_policy()
    
    return {
        "status": "healthy",
        "ai_review_enabled": policy.ai_review.enabled,
        "configured_models": len(policy.ai_review.models),
        "strategy": policy.ai_review.strategy,
    }
