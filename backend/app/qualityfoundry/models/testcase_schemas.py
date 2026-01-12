"""QualityFoundry - TestCase Schemas

测试用例相关的 Pydantic 数据模型
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

class TestStep(BaseModel):
    """测试步骤对"""
    step: str = Field(..., description="操作步骤")
    expected: str = Field(..., description="预期结果")


class TestCaseCreate(BaseModel):
    """创建测试用例请求"""
    scenario_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[TestStep] = Field(..., min_length=1)
    expected_results: Optional[list[str]] = Field(default_factory=list) # 兼容旧字段


class TestCaseUpdate(BaseModel):
    """更新测试用例请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    preconditions: Optional[list[str]] = None
    steps: Optional[list[TestStep]] = None
    expected_results: Optional[list[str]] = None


class TestCaseGenerateRequest(BaseModel):
    """AI 生成测试用例请求"""
    scenario_id: UUID
    auto_approve: bool = Field(default=False, description="是否自动批准")


# ============================================================
# Response Schemas
# ============================================================

class TestCaseResponse(BaseModel):
    """测试用例响应"""
    id: UUID
    scenario_id: UUID
    title: str
    preconditions: list[str]
    steps: list[TestStep]
    expected_results: list[str]
    approval_status: ApprovalStatus
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestCaseListResponse(BaseModel):
    """测试用例列表响应"""
    total: int
    items: list[TestCaseResponse]
    page: int
    page_size: int
