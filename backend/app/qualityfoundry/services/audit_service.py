"""Audit Service (PR-C)

审计日志写入与查询服务。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from qualityfoundry.database.audit_log_models import AuditEventType, AuditLog
from qualityfoundry.governance.repro import get_git_sha
from qualityfoundry.governance.policy_loader import get_policy

logger = logging.getLogger(__name__)


def is_audit_enabled() -> bool:
    """检查审计日志是否启用"""
    return os.getenv("AUDIT_LOG_ENABLED", "true").lower() in ("true", "1", "yes")


def _hash_args(args: dict[str, Any] | None) -> str | None:
    """计算参数哈希"""
    if not args:
        return None
    canonical = json.dumps(args, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _hash_policy() -> str | None:
    """计算策略哈希"""
    try:
        policy = get_policy()
        canonical = json.dumps(policy.model_dump(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
    except Exception:
        return None


def write_audit_event(
    db: Session,
    *,
    run_id: UUID,
    event_type: AuditEventType,
    user_id: UUID | None = None,  # 操作用户 ID（用于所有权过滤）
    tool_name: str | None = None,
    args: dict[str, Any] | None = None,
    status: str | None = None,
    duration_ms: int | None = None,
    decision_source: str | None = None,
    actor: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog | None:
    """
    写入审计事件。

    Args:
        db: 数据库会话
        run_id: 运行 ID
        event_type: 事件类型
        user_id: 操作用户 ID（可选，用于所有权过滤）
        tool_name: 工具名称（可选）
        args: 工具参数（可选，用于计算哈希）
        status: 状态（可选）
        duration_ms: 执行时长（可选）
        decision_source: 决策来源（可选）
        actor: 执行者（可选）
        details: 扩展信息（可选）

    Returns:
        创建的 AuditLog 记录，或 None（如果审计已禁用）
    """
    if not is_audit_enabled():
        logger.debug("Audit logging disabled, skipping event")
        return None

    try:
        log_entry = AuditLog(
            run_id=run_id,
            created_by_user_id=user_id,  # 记录操作用户
            ts=datetime.now(timezone.utc),
            event_type=event_type,
            actor=actor,
            tool_name=tool_name,
            args_hash=_hash_args(args),
            status=status,
            duration_ms=duration_ms,
            policy_hash=_hash_policy(),
            git_sha=get_git_sha(),
            decision_source=decision_source,
            details=json.dumps(details) if details else None,
        )

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        logger.info(f"Audit event logged: {event_type.value} run={run_id}")
        return log_entry

    except Exception as e:
        logger.exception(f"Failed to write audit event: {e}")
        db.rollback()
        return None


def query_audit_events(
    db: Session,
    run_id: UUID,
    *,
    event_types: list[AuditEventType] | None = None,
    limit: int = 1000,
) -> list[AuditLog]:
    """
    查询指定运行的审计事件。

    Args:
        db: 数据库会话
        run_id: 运行 ID
        event_types: 事件类型过滤（可选）
        limit: 返回数量限制

    Returns:
        按时间排序的审计事件列表
    """
    query = db.query(AuditLog).filter(AuditLog.run_id == run_id)

    if event_types:
        query = query.filter(AuditLog.event_type.in_(event_types))

    return query.order_by(AuditLog.ts.asc()).limit(limit).all()


def audit_event_to_dict(event: AuditLog) -> dict[str, Any]:
    """将审计事件转换为字典"""
    return {
        "id": str(event.id),
        "run_id": str(event.run_id),
        "ts": event.ts.isoformat(),
        "event_type": event.event_type.value,
        "actor": event.actor,
        "tool_name": event.tool_name,
        "args_hash": event.args_hash,
        "status": event.status,
        "duration_ms": event.duration_ms,
        "policy_hash": event.policy_hash,
        "git_sha": event.git_sha,
        "decision_source": event.decision_source,
        "details": json.loads(event.details) if event.details else None,
    }
