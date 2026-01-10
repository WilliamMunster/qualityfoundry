from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import uuid

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import Report, ReportType, Execution, ExecutionStatus

router = APIRouter(prefix="/reports", tags=["reports"])

# --- Schemas ---
class ReportBase(BaseModel):
    title: str
    type: str = ReportType.ON_DEMAND.value
    data: dict = {}

class ReportCreate(ReportBase):
    pass

from pydantic import BaseModel, field_serializer
from datetime import timezone

class ReportResponse(ReportBase):
    id: uuid.UUID
    created_at: datetime
    created_by: str
    
    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total: int
    success: int
    failed: int
    running: int

# --- Routes ---

@router.get("/dashboard-stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表板统计数据"""
    total = db.query(Execution).count()
    success = db.query(Execution).filter(Execution.status == ExecutionStatus.SUCCESS).count()
    failed = db.query(Execution).filter(Execution.status == ExecutionStatus.FAILED).count()
    running = db.query(Execution).filter(Execution.status == ExecutionStatus.RUNNING).count()
    
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "running": running
    }

@router.get("", response_model=List[ReportResponse])
def list_reports(
    skip: int = 0,
    limit: int = 20,
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取报告列表"""
    query = db.query(Report)
    if type:
        query = query.filter(Report.type == type)
    return query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()

@router.post("", response_model=ReportResponse, status_code=201)
def create_report(report_in: ReportCreate, db: Session = Depends(get_db)):
    """创建新报告"""
    report = Report(
        title=report_in.title,
        type=ReportType(report_in.type),
        data=report_in.data,
        created_by="system" # 暂定
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
