"""QualityFoundry - Tenant Service

多租户服务 - 提供租户 CRUD 和成员管理
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import or_

from qualityfoundry.database.tenant_models import Tenant, TenantMembership, TenantRole, TenantStatus
from qualityfoundry.database.user_models import User


class TenantService:
    """租户服务"""
    
    # ========== 租户 CRUD ==========
    
    @staticmethod
    def create_tenant(
        db: Session,
        slug: str,
        name: str,
        owner_id: UUID,
        description: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        max_projects: Optional[int] = None,
        max_users: Optional[int] = None,
        max_storage_mb: Optional[int] = None,
    ) -> Tenant:
        """创建租户
        
        Args:
            db: 数据库会话
            slug: 唯一标识
            name: 租户名称
            owner_id: 所有者用户ID
            description: 描述
            contact_email: 联系邮箱
            contact_phone: 联系电话
            max_projects: 最大项目数
            max_users: 最大用户数
            max_storage_mb: 最大存储(MB)
            
        Returns:
            创建的租户对象
            
        Raises:
            ValueError: 如果 slug 已存在
        """
        # 检查 slug 是否已存在
        existing = db.query(Tenant).filter(Tenant.slug == slug).first()
        if existing:
            raise ValueError(f"租户 slug '{slug}' 已存在")
        
        # 创建租户
        tenant = Tenant(
            slug=slug,
            name=name,
            description=description,
            status=TenantStatus.ACTIVE,
            contact_email=contact_email,
            contact_phone=contact_phone,
            max_projects=max_projects,
            max_users=max_users,
            max_storage_mb=max_storage_mb,
        )
        db.add(tenant)
        db.flush()  # 获取 tenant.id
        
        # 创建所有者成员关系
        membership = TenantMembership(
            tenant_id=tenant.id,
            user_id=owner_id,
            role=TenantRole.OWNER,
            is_active=True,
        )
        db.add(membership)
        db.commit()
        db.refresh(tenant)
        
        return tenant
    
    @staticmethod
    def get_tenant_by_id(db: Session, tenant_id: UUID) -> Optional[Tenant]:
        """通过 ID 获取租户"""
        return db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    @staticmethod
    def get_tenant_by_slug(db: Session, slug: str) -> Optional[Tenant]:
        """通过 slug 获取租户"""
        return db.query(Tenant).filter(Tenant.slug == slug).first()
    
    @staticmethod
    def list_tenants(
        db: Session,
        user_id: Optional[UUID] = None,
        status: Optional[TenantStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Tenant]:
        """列出租户
        
        Args:
            db: 数据库会话
            user_id: 筛选用户所属的租户
            status: 按状态筛选
            search: 搜索 slug 或 name
            skip: 分页偏移
            limit: 分页大小
            
        Returns:
            租户列表
        """
        query = db.query(Tenant)
        
        if user_id:
            # 筛选用户所属的租户
            query = query.join(TenantMembership).filter(
                TenantMembership.user_id == user_id,
                TenantMembership.is_active.is_(True)
            )
        
        if status:
            query = query.filter(Tenant.status == status)
        
        if search:
            search_filter = or_(
                Tenant.slug.ilike(f"%{search}%"),
                Tenant.name.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        query = query.offset(skip).limit(limit)
        return query.all()
    
    @staticmethod
    def update_tenant(
        db: Session,
        tenant_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[TenantStatus] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        max_projects: Optional[int] = None,
        max_users: Optional[int] = None,
        max_storage_mb: Optional[int] = None,
    ) -> Optional[Tenant]:
        """更新租户信息
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的租户对象，如果不存在返回 None
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return None
        
        if name is not None:
            tenant.name = name
        if description is not None:
            tenant.description = description
        if status is not None:
            tenant.status = status
        if contact_email is not None:
            tenant.contact_email = contact_email
        if contact_phone is not None:
            tenant.contact_phone = contact_phone
        if max_projects is not None:
            tenant.max_projects = max_projects
        if max_users is not None:
            tenant.max_users = max_users
        if max_storage_mb is not None:
            tenant.max_storage_mb = max_storage_mb
        
        tenant.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(tenant)
        return tenant
    
    @staticmethod
    def delete_tenant(db: Session, tenant_id: UUID) -> bool:
        """删除租户
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            
        Returns:
            是否成功删除
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False
        
        db.delete(tenant)
        db.commit()
        return True
    
    # ========== 成员管理 ==========
    
    @staticmethod
    def add_member(
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        role: TenantRole = TenantRole.MEMBER,
        allow_owner: bool = False,  # 仅内部使用，允许添加 owner
    ) -> TenantMembership:
        """添加成员到租户
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            user_id: 用户ID
            role: 角色（默认 member）
            allow_owner: 是否允许添加 owner 角色（内部使用）
            
        Returns:
            成员关系对象
            
        Raises:
            ValueError: 如果用户不存在、已是成员、或尝试添加 owner 角色
        """
        # F001: 验证用户存在
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        # 检查是否已存在
        existing = db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id
        ).first()
        
        if existing:
            raise ValueError("用户已经是该租户的成员")
        
        # F002: 禁止通过 add_member 添加 owner 角色（除非明确允许）
        if role == TenantRole.OWNER and not allow_owner:
            raise ValueError("不能直接添加所有者角色，请联系现有所有者")
        
        membership = TenantMembership(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            is_active=True,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership
    
    @staticmethod
    def remove_member(db: Session, tenant_id: UUID, user_id: UUID) -> bool:
        """从租户移除成员
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            user_id: 用户ID
            
        Returns:
            是否成功移除
        """
        membership = db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id
        ).first()
        
        if not membership:
            return False
        
        db.delete(membership)
        db.commit()
        return True
    
    @staticmethod
    def update_member_role(
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        role: TenantRole,
    ) -> Optional[TenantMembership]:
        """更新成员角色
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            user_id: 用户ID
            role: 新角色
            
        Returns:
            更新后的成员关系，如果不存在返回 None
        """
        membership = db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id
        ).first()
        
        if not membership:
            return None
        
        membership.role = role
        db.commit()
        db.refresh(membership)
        return membership
    
    @staticmethod
    def get_members(db: Session, tenant_id: UUID) -> List[TenantMembership]:
        """获取租户的所有成员
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            
        Returns:
            成员关系列表
        """
        return db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id
        ).all()
    
    @staticmethod
    def get_member(db: Session, tenant_id: UUID, user_id: UUID) -> Optional[TenantMembership]:
        """获取特定成员关系
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            user_id: 用户ID
            
        Returns:
            成员关系对象，如果不存在返回 None
        """
        return db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id
        ).first()
    
    @staticmethod
    def get_user_tenants(db: Session, user_id: UUID) -> List[Tenant]:
        """获取用户所属的所有租户
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            租户列表
        """
        memberships = db.query(TenantMembership).filter(
            TenantMembership.user_id == user_id,
            TenantMembership.is_active.is_(True)
        ).all()
        
        return [m.tenant for m in memberships]
    
    # ========== 权限检查 ==========
    
    @staticmethod
    def check_permission(
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        required_roles: List[TenantRole],
    ) -> bool:
        """检查用户是否有指定角色的权限
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            user_id: 用户ID
            required_roles: 要求的角色列表
            
        Returns:
            是否有权限
        """
        membership = db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
            TenantMembership.is_active.is_(True)
        ).first()
        
        if not membership:
            return False
        
        return membership.role in required_roles
    
    @staticmethod
    def is_owner(db: Session, tenant_id: UUID, user_id: UUID) -> bool:
        """检查用户是否是租户所有者"""
        return TenantService.check_permission(db, tenant_id, user_id, [TenantRole.OWNER])
    
    @staticmethod
    def is_admin(db: Session, tenant_id: UUID, user_id: UUID) -> bool:
        """检查用户是否是租户管理员（owner 或 admin）"""
        return TenantService.check_permission(db, tenant_id, user_id, [TenantRole.OWNER, TenantRole.ADMIN])
    
    @staticmethod
    def is_member(db: Session, tenant_id: UUID, user_id: UUID) -> bool:
        """检查用户是否是租户成员"""
        return TenantService.check_permission(
            db, tenant_id, user_id, [TenantRole.OWNER, TenantRole.ADMIN, TenantRole.MEMBER]
        )
