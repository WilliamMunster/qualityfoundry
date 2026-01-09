"""QualityFoundry - Approval Schemas

审核流程相关的 Pydantic 数据模型
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EntityType(str, Enum):
    """实体类型"""
    SCENARIO = "scenario"
    TESTCASE = "testcase"


# ============================================================
# Request Schemas
# ============================================================

class ApprovalCreate(BaseModel):
    """创建审核请求"""
    entity_type: EntityType
    entity_id: UUID
    reviewer: Optional[str] = None


class ApprovalDecision(BaseModel):
    """审核决策"""
    reviewer: str = Field(..., min_length=1, max_length=100)
    review_comment: Optional[str] = None


# ============================================================
# Response Schemas
# ============================================================

class ApprovalResponse(BaseModel):
    """审核响应"""
    id: UUID
    entity_type: str
    entity_id: UUID
    status: ApprovalStatus
    reviewer: Optional[str]
    review_comment: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalHistoryResponse(BaseModel):
    """审核历史响应"""
    total: int
    items: list[ApprovalResponse]
