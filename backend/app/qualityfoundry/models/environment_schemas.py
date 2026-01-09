"""QualityFoundry - Environment Schemas

环境配置相关的 Pydantic 数据模型
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# Request Schemas
# ============================================================

class EnvironmentCreate(BaseModel):
    """创建环境请求"""
    name: str = Field(..., min_length=1, max_length=100, description="环境名称（dev/sit/uat/prod）")
    base_url: str = Field(..., description="基础 URL")
    variables: dict = Field(default_factory=dict, description="环境变量")
    credentials: Optional[str] = Field(None, description="凭证（将被加密存储）")
    health_check_url: Optional[str] = Field(None, description="健康检查 URL")


class EnvironmentUpdate(BaseModel):
    """更新环境请求"""
    base_url: Optional[str] = None
    variables: Optional[dict] = None
    credentials: Optional[str] = None
    health_check_url: Optional[str] = None
    is_active: Optional[bool] = None


# ============================================================
# Response Schemas
# ============================================================

class EnvironmentResponse(BaseModel):
    """环境响应"""
    id: UUID
    name: str
    base_url: str
    variables: dict
    credentials: Optional[str]  # 加密后的凭证
    health_check_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnvironmentListResponse(BaseModel):
    """环境列表响应"""
    total: int
    items: list[EnvironmentResponse]


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    environment_id: UUID
    environment_name: str
    is_healthy: bool
    status_code: Optional[int]
    response_time_ms: Optional[float]
    error_message: Optional[str]
    checked_at: datetime
