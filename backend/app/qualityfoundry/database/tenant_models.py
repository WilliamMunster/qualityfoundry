"""QualityFoundry - Tenant Models

多租户数据模型
- Tenant: 租户/组织实体
- TenantMembership: 用户-租户成员关系
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from qualityfoundry.database.config import Base


class TenantStatus(str, enum.Enum):
    """租户状态"""
    ACTIVE = "active"      # 正常使用
    SUSPENDED = "suspended"  # 暂停使用
    PENDING = "pending"    # 待激活


class TenantRole(str, enum.Enum):
    """租户内角色"""
    OWNER = "owner"        # 所有者
    ADMIN = "admin"        # 管理员
    MEMBER = "member"      # 成员


class Tenant(Base):
    """租户模型（组织/工作空间）
    
    代表一个独立的工作空间，数据按租户隔离。
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.ACTIVE, nullable=False)
    
    # 联系信息
    contact_email = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    
    # 配额限制（可选，用于 SaaS 计费）
    max_projects = Column(Integer, nullable=True)  # None = 无限制
    max_users = Column(Integer, nullable=True)
    max_storage_mb = Column(Integer, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), 
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # 关联
    memberships = relationship("TenantMembership", back_populates="tenant", 
                               cascade="all, delete-orphan")
    
    @property
    def members(self):
        """获取所有成员用户"""
        return [m.user for m in self.memberships]
    
    def __repr__(self):
        return f"<Tenant(slug='{self.slug}', name='{self.name}')>"


class TenantMembership(Base):
    """租户成员关系模型
    
    用户与租户的多对多关系，包含角色信息。
    """
    __tablename__ = "tenant_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLEnum(TenantRole), default=TenantRole.MEMBER, nullable=False)
    
    # 成员状态
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 加入时间
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # 关联
    tenant = relationship("Tenant", back_populates="memberships")
    user = relationship("User", backref="tenant_memberships")
    
    # 唯一约束：一个用户在一个租户中只有一个成员关系
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
        Index("ix_tenant_memberships_user_id", "user_id"),
        Index("ix_tenant_memberships_tenant_id", "tenant_id"),
    )
    
    def __repr__(self):
        return f"<TenantMembership(tenant='{self.tenant_id}', user='{self.user_id}', role='{self.role}')>"
