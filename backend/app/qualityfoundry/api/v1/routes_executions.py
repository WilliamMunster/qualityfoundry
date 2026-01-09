"""QualityFoundry - Execution API Routes

执行管理 API 路由
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import (
    Execution,
    ExecutionMode as DBExecutionMode,
    ExecutionStatus as DBExecutionStatus,
)
from qualityfoundry.models.execution_schemas import (
    ExecutionCreate,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionStatusResponse,
)

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("", response_model=ExecutionResponse, status_code=201)
async def create_execution(
    req: ExecutionCreate,
    db: Session = Depends(get_db)
):
    """
    触发执行
    
    创建执行任务并异步执行测试用例
    """
    # 创建执行记录
    execution = Execution(
        testcase_id=req.testcase_id,
        environment_id=req.environment_id,
        mode=DBExecutionMode(req.mode.value),
        status=DBExecutionStatus.PENDING
    )
    
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    # TODO: 异步触发执行任务
    # 目前返回 pending 状态
    
    return execution


@router.get("", response_model=ExecutionListResponse)
def list_executions(
    testcase_id: Optional[UUID] = None,
    environment_id: Optional[UUID] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """执行列表"""
    query = db.query(Execution)
    
    # 按用例筛选
    if testcase_id:
        query = query.filter(Execution.testcase_id == testcase_id)
    
    # 按环境筛选
    if environment_id:
        query = query.filter(Execution.environment_id == environment_id)
    
    # 按状态筛选
    if status:
        query = query.filter(Execution.status == status)
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    items = query.order_by(Execution.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ExecutionListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    execution_id: UUID,
    db: Session = Depends(get_db)
):
    """执行详情"""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/{execution_id}/status", response_model=ExecutionStatusResponse)
def get_execution_status(
    execution_id: UUID,
    db: Session = Depends(get_db)
):
    """
    获取执行状态
    
    用于实时查询执行进度
    """
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # TODO: 实现实时进度查询
    return ExecutionStatusResponse(
        id=execution.id,
        status=execution.status,
        progress=None,
        current_step=None,
        message=None
    )


@router.post("/{execution_id}/stop", response_model=ExecutionResponse)
def stop_execution(
    execution_id: UUID,
    db: Session = Depends(get_db)
):
    """
    停止执行
    
    中止正在运行的执行任务
    """
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status != DBExecutionStatus.RUNNING:
        raise HTTPException(status_code=400, detail="执行未在运行中")
    
    # TODO: 实现停止逻辑
    execution.status = DBExecutionStatus.STOPPED
    execution.completed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(execution)
    
    return execution


@router.get("/{execution_id}/logs")
def get_execution_logs(
    execution_id: UUID,
    db: Session = Depends(get_db)
):
    """
    获取执行日志
    
    返回执行过程中的日志信息
    """
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # TODO: 实现日志查询
    return {
        "execution_id": str(execution.id),
        "logs": []
    }
