"""QualityFoundry - Approval API Routes

审核流程 API 路由
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import ApprovalStatus as DBApprovalStatus
from qualityfoundry.models.approval_schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalHistoryResponse,
    ApprovalResponse,
)
from qualityfoundry.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalResponse, status_code=201)
def create_approval(
    req: ApprovalCreate,
    db: Session = Depends(get_db)
):
    """创建审核"""
    service = ApprovalService(db)
    
    try:
        approval = service.create_approval(
            entity_type=req.entity_type.value,
            entity_id=req.entity_id,
            reviewer=req.reviewer
        )
        return approval
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ApprovalHistoryResponse)
def list_approvals(
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """审核列表"""
    service = ApprovalService(db)
    
    # 转换状态
    db_status = None
    if status:
        try:
            db_status = DBApprovalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的审核状态: {status}")
    
    items = service.get_approval_history(
        entity_type=entity_type,
        entity_id=entity_id,
        status=db_status
    )
    
    return ApprovalHistoryResponse(
        total=len(items),
        items=items
    )


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
def approve_approval(
    approval_id: UUID,
    req: ApprovalDecision,
    db: Session = Depends(get_db)
):
    """批准审核"""
    service = ApprovalService(db)
    
    try:
        approval = service.approve(
            approval_id=approval_id,
            reviewer=req.reviewer,
            comment=req.review_comment
        )
        return approval
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
def reject_approval(
    approval_id: UUID,
    req: ApprovalDecision,
    db: Session = Depends(get_db)
):
    """拒绝审核"""
    service = ApprovalService(db)
    
    try:
        approval = service.reject(
            approval_id=approval_id,
            reviewer=req.reviewer,
            comment=req.review_comment
        )
        return approval
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{approval_id}/history", response_model=list[ApprovalResponse])
def get_approval_history(
    approval_id: UUID,
    db: Session = Depends(get_db)
):
    """审核历史"""
    service = ApprovalService(db)
    
    items = service.get_approval_history(entity_id=approval_id)
    return items
