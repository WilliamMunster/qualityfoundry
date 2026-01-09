"""QualityFoundry - Scenario API Routes

场景管理 API 路由
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import (
    ApprovalStatus as DBApprovalStatus,
    Scenario,
)
from qualityfoundry.models.scenario_schemas import (
    ScenarioCreate,
    ScenarioGenerateRequest,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioUpdate,
)
from qualityfoundry.services.approval_service import ApprovalService

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/generate", response_model=list[ScenarioResponse], status_code=201)
async def generate_scenarios(
    req: ScenarioGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    AI 生成场景
    
    根据需求文档自动生成测试场景
    """
    # TODO: 集成 AI 生成服务
    # 目前返回示例场景
    
    scenario = Scenario(
        requirement_id=req.requirement_id,
        title="示例场景：用户登录",
        description="验证用户登录功能",
        steps=["打开登录页面", "输入用户名和密码", "点击登录按钮", "验证登录成功"],
        approval_status=DBApprovalStatus.APPROVED if req.auto_approve else DBApprovalStatus.PENDING,
        version="v1.0"
    )
    
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    # 如果不是自动批准，创建审核记录
    if not req.auto_approve:
        approval_service = ApprovalService(db)
        approval_service.create_approval(
            entity_type="scenario",
            entity_id=scenario.id
        )
    
    return [scenario]


@router.post("", response_model=ScenarioResponse, status_code=201)
def create_scenario(
    req: ScenarioCreate,
    db: Session = Depends(get_db)
):
    """创建场景"""
    scenario = Scenario(
        requirement_id=req.requirement_id,
        title=req.title,
        description=req.description,
        steps=req.steps,
        version="v1.0"
    )
    
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return scenario


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(
    requirement_id: Optional[UUID] = None,
    approval_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """场景列表"""
    query = db.query(Scenario)
    
    # 按需求筛选
    if requirement_id:
        query = query.filter(Scenario.requirement_id == requirement_id)
    
    # 按审核状态筛选
    if approval_status:
        query = query.filter(Scenario.approval_status == approval_status)
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    items = query.order_by(Scenario.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ScenarioListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: UUID,
    db: Session = Depends(get_db)
):
    """场景详情"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: UUID,
    req: ScenarioUpdate,
    db: Session = Depends(get_db)
):
    """更新场景"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # 更新字段
    if req.title is not None:
        scenario.title = req.title
    if req.description is not None:
        scenario.description = req.description
    if req.steps is not None:
        scenario.steps = req.steps
    
    db.commit()
    db.refresh(scenario)
    return scenario


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: UUID,
    db: Session = Depends(get_db)
):
    """删除场景"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    db.delete(scenario)
    db.commit()
    return None


@router.post("/{scenario_id}/approve", response_model=ScenarioResponse)
def approve_scenario(
    scenario_id: UUID,
    reviewer: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """审核场景（批准）"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # 使用审核服务
    approval_service = ApprovalService(db)
    
    # 查找待审核记录
    approvals = approval_service.get_approval_history(
        entity_type="scenario",
        entity_id=scenario_id,
        status=DBApprovalStatus.PENDING
    )
    
    if not approvals:
        raise HTTPException(status_code=400, detail="没有待审核记录")
    
    # 批准第一个待审核记录
    approval_service.approve(
        approval_id=approvals[0].id,
        reviewer=reviewer,
        comment=comment
    )
    
    db.refresh(scenario)
    return scenario


@router.post("/{scenario_id}/reject", response_model=ScenarioResponse)
def reject_scenario(
    scenario_id: UUID,
    reviewer: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """审核场景（拒绝）"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # 使用审核服务
    approval_service = ApprovalService(db)
    
    # 查找待审核记录
    approvals = approval_service.get_approval_history(
        entity_type="scenario",
        entity_id=scenario_id,
        status=DBApprovalStatus.PENDING
    )
    
    if not approvals:
        raise HTTPException(status_code=400, detail="没有待审核记录")
    
    # 拒绝第一个待审核记录
    approval_service.reject(
        approval_id=approvals[0].id,
        reviewer=reviewer,
        comment=comment
    )
    
    db.refresh(scenario)
    return scenario
