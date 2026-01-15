"""QualityFoundry - Requirement API Routes

需求管理 API 路由
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import Requirement, RequirementStatus as DBRequirementStatus
from qualityfoundry.models.requirement_schemas import (
    RequirementCreate,
    RequirementListResponse,
    RequirementResponse,
    RequirementUpdate,
    RequirementVersionCreate,
    RequirementVersionResponse,
)
from qualityfoundry.models.common_schemas import BulkDeleteRequest, BulkDeleteResponse

router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.post("", response_model=RequirementResponse, status_code=201)
def create_requirement(
    req: RequirementCreate,
    db: Session = Depends(get_db)
):
    """创建需求"""
    requirement = Requirement(
        title=req.title,
        content=req.content,
        file_path=req.file_path,
        version=req.version,
        created_by=req.created_by,
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@router.get("", response_model=RequirementListResponse)
def list_requirements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """需求列表（分页、搜索、筛选）"""
    query = db.query(Requirement)
    
    # 状态筛选
    if status:
        query = query.filter(Requirement.status == status)
    
    # 搜索（标题或内容）
    if search:
        query = query.filter(
            (Requirement.title.contains(search)) | 
            (Requirement.content.contains(search))
        )
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    items = query.order_by(Requirement.created_at.desc()).offset(offset).limit(page_size).all()
    
    return RequirementListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


@router.get("/{requirement_id}", response_model=RequirementResponse)
def get_requirement(
    requirement_id: UUID,
    db: Session = Depends(get_db)
):
    """需求详情"""
    requirement = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement


@router.put("/{requirement_id}", response_model=RequirementResponse)
def update_requirement(
    requirement_id: UUID,
    req: RequirementUpdate,
    db: Session = Depends(get_db)
):
    """更新需求"""
    requirement = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    # 更新字段
    if req.title is not None:
        requirement.title = req.title
    if req.content is not None:
        requirement.content = req.content
    if req.status is not None:
        requirement.status = DBRequirementStatus(req.status.value)
    
    db.commit()
    db.refresh(requirement)
    return requirement


@router.delete("/{requirement_id}", status_code=204)
def delete_requirement(
    requirement_id: UUID,
    db: Session = Depends(get_db)
):
    """删除需求"""
    requirement = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    db.delete(requirement)
    db.commit()
    return None


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_requirements(
    req: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """批量删除需求"""
    deleted_count = 0
    failed_ids = []

    for req_id in req.ids:
        requirement = db.query(Requirement).filter(Requirement.id == req_id).first()
        if requirement:
            db.delete(requirement)
            deleted_count += 1
        else:
            failed_ids.append(req_id)

    db.commit()

    return BulkDeleteResponse(
        deleted_count=deleted_count,
        failed_ids=failed_ids
    )


@router.post("/{requirement_id}/versions", response_model=RequirementResponse, status_code=201)
def create_requirement_version(
    requirement_id: UUID,
    req: RequirementVersionCreate,
    db: Session = Depends(get_db)
):
    """创建需求新版本"""
    # 获取原需求
    original = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    # 创建新版本（复制原需求，更新内容和版本号）
    new_version = Requirement(
        title=original.title,
        content=req.content,
        file_path=original.file_path,
        version=req.version,
        created_by=original.created_by,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


@router.get("/{requirement_id}/versions", response_model=list[RequirementVersionResponse])
def list_requirement_versions(
    requirement_id: UUID,
    db: Session = Depends(get_db)
):
    """需求版本历史"""
    # 获取原需求
    original = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    # 查找所有同标题的需求（作为版本历史）
    versions = db.query(Requirement).filter(
        Requirement.title == original.title
    ).order_by(Requirement.created_at.desc()).all()
    
    return versions
