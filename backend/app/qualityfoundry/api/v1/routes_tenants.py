"""QualityFoundry - Tenant Routes

多租户管理 API 路由
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.user_models import User
from qualityfoundry.database.tenant_models import TenantRole, TenantStatus
from qualityfoundry.api.deps.auth_deps import get_current_user
from qualityfoundry.services.tenant_service import TenantService
from qualityfoundry.models.tenant_schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantMemberCreate,
    TenantMemberUpdate,
    TenantMemberResponse,
    TenantListResponse,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse, status_code=201)
def create_tenant(
    data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建租户
    
    当前用户自动成为租户所有者。
    """
    try:
        tenant = TenantService.create_tenant(
            db=db,
            slug=data.slug,
            name=data.name,
            owner_id=current_user.id,
            description=data.description,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            max_projects=data.max_projects,
            max_users=data.max_users,
            max_storage_mb=data.max_storage_mb,
        )
        return tenant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TenantListResponse)
def list_tenants(
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出租户
    
    普通用户只能看到自己所属的租户，管理员可以看到所有租户。
    """
    # 解析状态
    tenant_status = None
    if status:
        try:
            tenant_status = TenantStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
    
    # 普通用户只返回自己的租户
    user_id = current_user.id
    if current_user.role.value == "admin":
        user_id = None  # 管理员可以看所有
    
    tenants = TenantService.list_tenants(
        db=db,
        user_id=user_id,
        status=tenant_status,
        search=search,
        skip=skip,
        limit=limit,
    )
    
    return TenantListResponse(
        items=tenants,
        total=len(tenants),
        skip=skip,
        limit=limit,
    )


@router.get("/my", response_model=List[TenantResponse])
def get_my_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的所有租户"""
    return TenantService.get_user_tenants(db, current_user.id)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取租户详情"""
    tenant = TenantService.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # 检查权限（成员才能查看）
    if not TenantService.is_member(db, tenant_id, current_user.id):
        raise HTTPException(status_code=403, detail="没有权限访问此租户")
    
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新租户信息
    
    只有管理员或所有者可以更新。
    """
    # 检查权限
    if not TenantService.is_admin(db, tenant_id, current_user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 解析状态
    status = None
    if data.status:
        try:
            status = TenantStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {data.status}")
    
    tenant = TenantService.update_tenant(
        db=db,
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        status=status,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        max_projects=data.max_projects,
        max_users=data.max_users,
        max_storage_mb=data.max_storage_mb,
    )
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    return tenant


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除租户
    
    只有所有者可以删除租户。
    """
    # 检查权限
    if not TenantService.is_owner(db, tenant_id, current_user.id):
        raise HTTPException(status_code=403, detail="需要所有者权限")
    
    success = TenantService.delete_tenant(db, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    return None


# ========== 成员管理 ==========

@router.get("/{tenant_id}/members", response_model=List[TenantMemberResponse])
def list_members(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取租户成员列表"""
    # 检查权限
    if not TenantService.is_member(db, tenant_id, current_user.id):
        raise HTTPException(status_code=403, detail="没有权限访问此租户")
    
    memberships = TenantService.get_members(db, tenant_id)
    
    # 转换为响应格式
    result = []
    for m in memberships:
        result.append(TenantMemberResponse(
            id=m.id,
            tenant_id=m.tenant_id,
            user_id=m.user_id,
            username=m.user.username,
            email=m.user.email,
            role=m.role.value,
            is_active=m.is_active,
            joined_at=m.joined_at,
        ))
    
    return result


@router.post("/{tenant_id}/members", response_model=TenantMemberResponse, status_code=201)
def add_member(
    tenant_id: UUID,
    data: TenantMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加成员到租户
    
    只有管理员可以添加成员。
    """
    # 检查权限
    if not TenantService.is_admin(db, tenant_id, current_user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 解析角色
    try:
        role = TenantRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的角色: {data.role}")
    
    try:
        membership = TenantService.add_member(
            db=db,
            tenant_id=tenant_id,
            user_id=data.user_id,
            role=role,
        )
        
        return TenantMemberResponse(
            id=membership.id,
            tenant_id=membership.tenant_id,
            user_id=membership.user_id,
            username=membership.user.username,
            email=membership.user.email,
            role=membership.role.value,
            is_active=membership.is_active,
            joined_at=membership.joined_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{tenant_id}/members/{user_id}", response_model=TenantMemberResponse)
def update_member(
    tenant_id: UUID,
    user_id: UUID,
    data: TenantMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新成员角色
    
    只有管理员可以更新成员角色。不能修改所有者的角色。
    """
    # 检查权限
    if not TenantService.is_admin(db, tenant_id, current_user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 解析角色
    try:
        role = TenantRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的角色: {data.role}")
    
    # 不能修改所有者角色
    if TenantService.is_owner(db, tenant_id, user_id):
        raise HTTPException(status_code=403, detail="不能修改所有者的角色")
    
    membership = TenantService.update_member_role(db, tenant_id, user_id, role)
    if not membership:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    return TenantMemberResponse(
        id=membership.id,
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        username=membership.user.username,
        email=membership.user.email,
        role=membership.role.value,
        is_active=membership.is_active,
        joined_at=membership.joined_at,
    )


@router.delete("/{tenant_id}/members/{user_id}", status_code=204)
def remove_member(
    tenant_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """移除成员
    
    只有管理员可以移除成员。不能移除所有者。
    """
    # 检查权限
    if not TenantService.is_admin(db, tenant_id, current_user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 不能移除所有者
    if TenantService.is_owner(db, tenant_id, user_id):
        raise HTTPException(status_code=403, detail="不能移除所有者")
    
    success = TenantService.remove_member(db, tenant_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    return None
