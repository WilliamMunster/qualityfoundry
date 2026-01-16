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
    TestCase,
    ExecutionMode as DBExecutionMode,
    ExecutionStatus as DBExecutionStatus,
)
from qualityfoundry.models.execution_schemas import (
    ExecutionCreate,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionStatusResponse,
)
from qualityfoundry.services.execution.async_executor import (
    get_task_manager,
)

router = APIRouter(prefix="/executions", tags=["executions"])


async def _execute_testcase(
    execution_id: UUID,
    testcase_id: UUID,
    environment_id: Optional[UUID],
    mode: str,
    _task_manager=None,
    _task_id=None,
    **kwargs
):
    """
    实际执行测试用例的函数（在后台任务中运行）
    
    Args:
        execution_id: 执行记录 ID
        testcase_id: 测试用例 ID
        environment_id: 环境 ID
        mode: 执行模式 (dsl/mcp/hybrid)
        _task_manager: 任务管理器（由 async_executor 注入）
        _task_id: 任务 ID（由 async_executor 注入）
    """
    import asyncio
    from qualityfoundry.database.config import SessionLocal
    
    # 创建独立的数据库会话（后台任务需要自己的会话）
    db = SessionLocal()
    
    try:
        # 获取执行记录
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise Exception(f"执行记录不存在: {execution_id}")
        
        # 更新状态为 RUNNING
        execution.status = DBExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        db.commit()
        
        if _task_manager and _task_id:
            _task_manager.update_progress(_task_id, 10, "初始化执行环境", "准备测试用例")
            _task_manager.add_log(_task_id, f"开始执行测试用例: {testcase_id}")
        
        # 获取测试用例
        testcase = db.query(TestCase).filter(TestCase.id == testcase_id).first()
        if not testcase:
            raise Exception(f"测试用例不存在: {testcase_id}")
        
        if _task_manager and _task_id:
            _task_manager.update_progress(_task_id, 30, "加载测试用例", f"用例: {testcase.title}")
            _task_manager.add_log(_task_id, f"测试用例: {testcase.title}")
        
        # 模拟执行步骤
        total_steps = len(testcase.steps) if testcase.steps else 1
        for i, step in enumerate(testcase.steps or ["默认步骤"], 1):
            if _task_manager and _task_id:
                progress = 30 + int(60 * i / total_steps)
                _task_manager.update_progress(_task_id, progress, f"执行步骤 {i}/{total_steps}", str(step))
                _task_manager.add_log(_task_id, f"步骤 {i}: {step}")
            
            # 模拟步骤执行时间
            await asyncio.sleep(0.5)
        
        # 执行完成
        execution.status = DBExecutionStatus.SUCCESS
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        if _task_manager and _task_id:
            _task_manager.update_progress(_task_id, 100, "执行完成", "所有步骤已完成")
            _task_manager.add_log(_task_id, "执行成功")
        
        return {
            "status": "success",
            "execution_id": str(execution_id),
            "testcase_id": str(testcase_id),
        }
        
    except Exception as e:
        # 更新为失败状态
        if execution:
            execution.status = DBExecutionStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
        
        if _task_manager and _task_id:
            _task_manager.add_log(_task_id, f"执行失败: {str(e)}")
        
        # [NEW] 触发 AI 诊断
        try:
            from qualityfoundry.services.observer_service import ObserverService
            # 使用默认配置进行异步诊断分析
            await ObserverService.analyze_execution_failure(db, execution_id)
            db.commit() # 在此处提交诊断结果
            if _task_manager and _task_id:
                _task_manager.add_log(_task_id, "AI 诊断已完成并记录。")
        except Exception as ai_err:
            logger.error(f"AI 诊断触发失败: {ai_err}")

        raise
        
    finally:
        db.close()


@router.post("", response_model=ExecutionResponse, status_code=201)
async def create_execution(
    req: ExecutionCreate,
    db: Session = Depends(get_db)
):
    """
    触发执行
    
    创建执行任务并异步执行测试用例
    注意：只有审核通过的用例才能执行
    """
    from qualityfoundry.database.models import ApprovalStatus as DBApprovalStatus
    
    # 0. 检查用例是否存在且已审核通过
    testcase = db.query(TestCase).filter(TestCase.id == req.testcase_id).first()
    if not testcase:
        raise HTTPException(status_code=404, detail="测试用例未找到")
    
    if testcase.approval_status != DBApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=400, 
            detail=f"测试用例尚未审核通过，当前状态: {testcase.approval_status.value}。请先审核通过用例后再执行。"
        )
    
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
    
    # 异步触发执行任务
    task_manager = get_task_manager()
    await task_manager.submit_task(
        execution_id=execution.id,
        executor_func=_execute_testcase,
        testcase_id=req.testcase_id,
        environment_id=req.environment_id,
        mode=req.mode.value,
    )
    
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
async def get_execution_status(
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
    
    # 从任务管理器获取实时进度
    task_manager = get_task_manager()
    task_info = await task_manager.get_task_by_execution(execution_id)
    
    if task_info:
        return ExecutionStatusResponse(
            id=execution.id,
            status=execution.status,
            progress=task_info.progress.progress,
            current_step=task_info.progress.current_step,
            message=task_info.progress.message
        )
    
    # 没有任务信息，返回数据库状态
    return ExecutionStatusResponse(
        id=execution.id,
        status=execution.status,
        progress=100 if execution.status in [DBExecutionStatus.SUCCESS, DBExecutionStatus.FAILED] else None,
        current_step=None,
        message=None
    )


@router.post("/{execution_id}/stop", response_model=ExecutionResponse)
async def stop_execution(
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
    
    # 取消后台任务
    task_manager = get_task_manager()
    cancelled = await task_manager.cancel_by_execution(execution_id)
    
    if cancelled:
        execution.status = DBExecutionStatus.STOPPED
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(execution)
    
    return execution


@router.get("/{execution_id}/logs")
async def get_execution_logs(
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
    
    # 从任务管理器获取日志
    task_manager = get_task_manager()
    logs = await task_manager.get_logs_by_execution(execution_id)
    
    return {
        "execution_id": str(execution.id),
        "logs": logs
    }

