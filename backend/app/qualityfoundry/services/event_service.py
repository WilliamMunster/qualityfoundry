"""Event Service (Dashboard P3)

处理运行事件的发布与检索。
"""

import json
from uuid import UUID
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from qualityfoundry.database.run_event_models import RunEvent


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def emit_event(self, run_id: UUID, event_type: str, data: Optional[dict] = None) -> RunEvent:
        """发布一个运行事件"""
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            data=json.dumps(data) if data else None,
            ts=datetime.now(timezone.utc)
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_events(self, run_id: UUID, last_event_id: Optional[str] = None) -> List[RunEvent]:
        """获取指定运行的事件列表
        
        支持 Last-Event-ID 补发。
        """
        query = self.db.query(RunEvent).filter(RunEvent.run_id == run_id)
        
        if last_event_id:
            try:
                last_uuid = UUID(last_event_id)
                last_event = self.db.query(RunEvent).filter(RunEvent.id == last_uuid).first()
                if last_event:
                    # 获取该事件之后的所有事件
                    query = query.filter(RunEvent.ts > last_event.ts)
            except ValueError:
                pass
                
        return query.order_by(RunEvent.ts.asc()).all()
