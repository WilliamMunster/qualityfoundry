"""Audit API Routes (PR-C)

审计日志查询路由。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.services.audit_service import (
    audit_event_to_dict,
    is_audit_enabled,
    query_audit_events,
)

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    """审计事件响应"""
    id: str
    run_id: str
    ts: str
    event_type: str
    actor: str | None
    tool_name: str | None
    args_hash: str | None
    status: str | None
    duration_ms: int | None
    policy_hash: str | None
    git_sha: str | None
    decision_source: str | None
    details: dict | None


class AuditQueryResponse(BaseModel):
    """审计查询响应"""
    run_id: str
    events: list[AuditEventResponse]
    count: int
    audit_enabled: bool


@router.get("/{run_id}", response_model=AuditQueryResponse)
def get_audit_events(
    run_id: UUID,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    """
    查询指定运行的审计事件。

    Args:
        run_id: 运行 ID
        limit: 返回数量限制（默认 1000）

    Returns:
        按时间排序的审计事件列表
    """
    if not is_audit_enabled():
        return AuditQueryResponse(
            run_id=str(run_id),
            events=[],
            count=0,
            audit_enabled=False,
        )

    events = query_audit_events(db, run_id, limit=limit)

    return AuditQueryResponse(
        run_id=str(run_id),
        events=[AuditEventResponse(**audit_event_to_dict(e)) for e in events],
        count=len(events),
        audit_enabled=True,
    )
