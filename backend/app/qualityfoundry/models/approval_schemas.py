"""QualityFoundry - Approval Schemas

审核流程相关的 Pydantic 数据模型
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class SingleApprovalRequest(BaseModel):
    """单体审核请求"""
    reviewer: str = Field(..., min_length=1, max_length=100)
    comment: Optional[str] = None


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

    model_config = ConfigDict(from_attributes=True)


class ApprovalHistoryResponse(BaseModel):
    """审核历史响应"""
    total: int
    items: list[ApprovalResponse]


class BatchApprovalRequest(BaseModel):
    """批量审核请求"""
    entity_type: EntityType
    entity_ids: list[UUID]
    reviewer: str = Field(..., min_length=1, max_length=100)
    comment: Optional[str] = None


class BatchApprovalResult(BaseModel):
    """单个实体的批量审核结果"""
    entity_id: str
    status: str
    success: bool
    note: Optional[str] = None
    error: Optional[str] = None


class BatchApprovalResponse(BaseModel):
    """批量审核响应"""
    total: int
    success_count: int
    failed_count: int
    results: list[BatchApprovalResult]
