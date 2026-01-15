"""QualityFoundry - Common Schemas

通用的 Pydantic 数据模型
"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# Bulk Operation Schemas
# ============================================================

class BulkDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: list[UUID] = Field(..., min_length=1, description="要删除的ID列表")


class BulkDeleteResponse(BaseModel):
    """批量删除响应"""
    deleted_count: int = Field(..., description="成功删除的数量")
    failed_ids: list[UUID] = Field(default_factory=list, description="删除失败的ID列表")
