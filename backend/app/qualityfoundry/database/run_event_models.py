"""Run Event Models (Dashboard P3)

记录运行过程中的实时事件，用于 SSE 服务端推送。
"""

import uuid
from datetime import datetime, timezone


from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from qualityfoundry.database.config import Base


class RunEvent(Base):
    """运行事件表"""

    __tablename__ = "run_events"

    # 使用 UUID v4 作为 event_id，ts 用于排序
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # 事件类型: run.started, run.finished, run.decided
    event_type = Column(String(50), nullable=False, index=True)
    
    # 事件数据 (JSON 字符串)
    data = Column(Text, nullable=True)
    
    # 时间戳
    ts = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<RunEvent {self.id} type={self.event_type} run={self.run_id}>"
