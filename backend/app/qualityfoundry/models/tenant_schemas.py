"""QualityFoundry - Tenant Schemas

多租户 Pydantic 模型
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    """创建租户"""
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    max_projects: Optional[int] = None
    max_users: Optional[int] = None
    max_storage_mb: Optional[int] = None


class TenantUpdate(BaseModel):
    """更新租户"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    max_projects: Optional[int] = None
    max_users: Optional[int] = None
    max_storage_mb: Optional[int] = None


class TenantResponse(BaseModel):
    """租户响应"""
    id: UUID
    slug: str
    name: str
    description: Optional[str]
    status: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    max_projects: Optional[int]
    max_users: Optional[int]
    max_storage_mb: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantMemberCreate(BaseModel):
    """添加租户成员"""
    user_id: UUID
    role: str = "member"  # owner, admin, member


class TenantMemberUpdate(BaseModel):
    """更新租户成员"""
    role: str  # owner, admin, member


class TenantMemberResponse(BaseModel):
    """租户成员响应"""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    username: str
    email: Optional[str]
    role: str
    is_active: bool
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantListResponse(BaseModel):
    """租户列表响应"""
    items: List[TenantResponse]
    total: int
    skip: int
    limit: int
