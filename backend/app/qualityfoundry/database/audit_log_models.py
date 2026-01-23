"""Audit Log Models (PR-C)

审计日志 ORM 模型，记录工具执行与决策事件。
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from qualityfoundry.database.config import Base


class AuditEventType(str, enum.Enum):
    """审计事件类型"""
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    DECISION_MADE = "decision_made"
    POLICY_BLOCKED = "policy_blocked"
    GOVERNANCE_SHORT_CIRCUIT = "governance_short_circuit"


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ts = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # 事件信息
    event_type = Column(Enum(AuditEventType), nullable=False, index=True)
    actor = Column(String(255), nullable=True)

    # 工具相关（可空）
    tool_name = Column(String(255), nullable=True)
    args_hash = Column(String(64), nullable=True)
    status = Column(String(50), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # 策略与可重现性
    policy_hash = Column(String(64), nullable=True)
    git_sha = Column(String(64), nullable=True)
    decision_source = Column(String(100), nullable=True)

    # 扩展信息
    details = Column(Text, nullable=True)  # JSON 字符串

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} {self.event_type.value} run={self.run_id}>"
