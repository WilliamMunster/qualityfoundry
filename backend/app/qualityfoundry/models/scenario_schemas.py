"""QualityFoundry - Scenario Schemas

场景管理相关的 Pydantic 数据模型
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from qualityfoundry.models.approval_schemas import ApprovalStatus


# ============================================================
# Request Schemas
# ============================================================

class ScenarioCreate(BaseModel):
    """创建场景请求"""
    requirement_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    steps: list[str] = Field(default_factory=list)


class ScenarioUpdate(BaseModel):
    """更新场景请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    steps: Optional[list[str]] = None


class ScenarioGenerateRequest(BaseModel):
    """AI 生成场景请求"""
    requirement_id: UUID
    auto_approve: bool = Field(default=False, description="是否自动批准")


# ============================================================
# Response Schemas
# ============================================================

class ScenarioResponse(BaseModel):
    """场景响应"""
    id: UUID
    seq_id: Optional[int] = None
    requirement_id: UUID
    requirement_seq_id: Optional[int] = None  # 关联需求的 seq_id
    title: str
    description: Optional[str]
    steps: list[str]
    approval_status: ApprovalStatus
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScenarioListResponse(BaseModel):
    """场景列表响应"""
    total: int
    items: list[ScenarioResponse]
    page: int
    page_size: int
