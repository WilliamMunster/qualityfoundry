"""QualityFoundry - Observer Schemas

上帝视角 API 响应模型
"""
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

class ObserverBaseResponse(BaseModel):
    """上帝视角基础响应"""
    status: str = Field(..., description="状态 (success/failed)")
    error: Optional[str] = Field(None, description="错误信息")

class ConsistencyResponse(ObserverBaseResponse):
    """一致性分析响应"""
    requirement_id: UUID
    analysis: str = Field(..., description="全链路一致性分析结果")

class CoverageResponse(ObserverBaseResponse):
    """覆盖度评估响应"""
    requirement_id: UUID
    coverage_analysis: str = Field(..., description="测试覆盖度评估结果")

class GodSuggestionsResponse(ObserverBaseResponse):
    """上帝建议响应"""
    requirement_id: UUID
    suggestions: str = Field(..., description="全局改进建议")

class ExecutionAnalysisResponse(ObserverBaseResponse):
    """执行失败诊断响应"""
    execution_id: UUID
    ai_analysis: str = Field(..., description="AI 故障诊断分析结果")
