"""QualityFoundry - Requirement Schemas

需求管理相关的 Pydantic 数据模型
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class RequirementStatus(str, Enum):
    """需求状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


# ============================================================
# Request Schemas
# ============================================================

class RequirementCreate(BaseModel):
    """创建需求请求"""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    file_path: Optional[str] = None
    version: str = Field(default="v1.0", max_length=50)
    created_by: str = Field(default="system", max_length=100)


class RequirementUpdate(BaseModel):
    """更新需求请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[RequirementStatus] = None


class RequirementVersionCreate(BaseModel):
    """创建需求新版本请求"""
    content: str = Field(..., min_length=1)
    version: str = Field(..., max_length=50)


# ============================================================
# Response Schemas
# ============================================================

from datetime import timezone

class RequirementResponse(BaseModel):
    """需求响应"""
    id: UUID
    title: str
    content: str
    file_path: Optional[str]
    version: str
    status: RequirementStatus
    created_by: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)


class RequirementListResponse(BaseModel):
    """需求列表响应"""
    total: int
    items: list[RequirementResponse]
    page: int
    page_size: int


class RequirementVersionResponse(BaseModel):
    """需求版本响应"""
    id: UUID
    version: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
