"""QualityFoundry - Execution Schemas

执行管理相关的 Pydantic 数据模型
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ExecutionMode(str, Enum):
    """执行模式"""
    DSL = "dsl"  # 使用现有 DSL 执行器
    MCP = "mcp"  # 使用 Playwright MCP
    HYBRID = "hybrid"  # 智能选择


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"


# ============================================================
# Request Schemas
# ============================================================

class ExecutionCreate(BaseModel):
    """创建执行请求"""
    testcase_id: UUID
    environment_id: UUID
    mode: ExecutionMode = Field(default=ExecutionMode.DSL, description="执行模式")


class ExecutionStop(BaseModel):
    """停止执行请求"""
    reason: Optional[str] = None


# ============================================================
# Response Schemas
# ============================================================

class ExecutionResponse(BaseModel):
    """执行响应"""
    id: UUID
    testcase_id: UUID
    environment_id: UUID
    mode: ExecutionMode
    status: ExecutionStatus
    result: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    @field_serializer("started_at", "completed_at", "created_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        # 强制添加 UTC 时区信息并格式化为带 Z 的 ISO 字符串
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)


class ExecutionListResponse(BaseModel):
    """执行列表响应"""
    total: int
    items: list[ExecutionResponse]
    page: int
    page_size: int


class ExecutionStatusResponse(BaseModel):
    """执行状态响应"""
    id: UUID
    status: ExecutionStatus
    progress: Optional[float] = Field(None, description="进度（0-100）")
    current_step: Optional[str] = None
    message: Optional[str] = None


class ExecutionLogResponse(BaseModel):
    """执行日志响应"""
    timestamp: datetime
    level: str
    message: str
