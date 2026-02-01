"""多租户功能测试

测试 Tenant/TenantMembership 模型和 TenantContext。
"""
from uuid import uuid4

import pytest
from fastapi import Request

from qualityfoundry.core.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_tenant,
)
from qualityfoundry.database.tenant_models import Tenant, TenantMembership, TenantRole, TenantStatus
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.services.auth_service import AuthService


class TestTenantModel:
    """Tenant 模型测试"""

    def test_create_tenant(self, db):
        """创建租户"""
        tenant = Tenant(
            id=uuid4(),
            slug="test-tenant",
            name="Test Tenant",
            description="A test tenant",
            status=TenantStatus.ACTIVE,
            contact_email="test@example.com",
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        
        assert tenant.slug == "test-tenant"
        assert tenant.name == "Test Tenant"
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.contact_email == "test@example.com"

    def test_tenant_unique_slug(self, db):
        """租户 slug 必须唯一"""
        tenant1 = Tenant(
            id=uuid4(),
            slug="unique-slug",
            name="Tenant 1",
        )
        db.add(tenant1)
        db.commit()
        
        # 尝试创建相同 slug 的租户应该失败
        tenant2 = Tenant(
            id=uuid4(),
            slug="unique-slug",  # 重复的 slug
            name="Tenant 2",
        )
        db.add(tenant2)
        
        with pytest.raises(Exception):
            db.commit()
        db.rollback()


class TestTenantMembership:
    """TenantMembership 模型测试"""

    def test_create_membership(self, db):
        """创建租户成员关系"""
        # 创建用户
        user = User(
            id=uuid4(),
            username=f"member_test_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="member@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        
        # 创建租户
        tenant = Tenant(
            id=uuid4(),
            slug="member-tenant",
            name="Member Tenant",
        )
        db.add(tenant)
        db.commit()
        
        # 创建成员关系
        membership = TenantMembership(
            id=uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            role=TenantRole.ADMIN,
            is_active=True,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        
        assert membership.role == TenantRole.ADMIN
        assert membership.is_active is True
        assert membership.tenant_id == tenant.id
        assert membership.user_id == user.id

    def test_unique_tenant_user_constraint(self, db):
        """用户在同一租户中只能有一个成员关系"""
        user = User(
            id=uuid4(),
            username=f"unique_test_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="unique@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        
        tenant = Tenant(
            id=uuid4(),
            slug="unique-tenant",
            name="Unique Tenant",
        )
        db.add(tenant)
        db.commit()
        
        # 第一个成员关系
        membership1 = TenantMembership(
            id=uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            role=TenantRole.MEMBER,
        )
        db.add(membership1)
        db.commit()
        
        # 第二个成员关系应该失败
        membership2 = TenantMembership(
            id=uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            role=TenantRole.ADMIN,
        )
        db.add(membership2)
        
        with pytest.raises(Exception):
            db.commit()
        db.rollback()


class TestJWTWithTenant:
    """JWT 多租户字段测试"""

    def test_jwt_without_tenant(self, db):
        """不包含租户信息的 JWT"""
        user = User(
            id=uuid4(),
            username=f"no_tenant_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="notenant@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_jwt_token(user)
        payload = AuthService.decode_jwt_token(token)
        
        assert "tenant_id" not in payload
        assert "tenant_role" not in payload
        assert payload["sub"] == str(user.id)

    def test_jwt_with_tenant(self, db):
        """包含租户信息的 JWT"""
        user = User(
            id=uuid4(),
            username=f"with_tenant_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="withtenant@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        tenant_id = str(uuid4())
        token = AuthService.create_jwt_token(
            user,
            tenant_id=tenant_id,
            tenant_role="admin"
        )
        payload = AuthService.decode_jwt_token(token)
        
        assert payload["tenant_id"] == tenant_id
        assert payload["tenant_role"] == "admin"
        assert payload["sub"] == str(user.id)

    def test_get_tenant_from_token(self, db):
        """从 token 提取租户信息"""
        user = User(
            id=uuid4(),
            username=f"extract_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="extract@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        tenant_id = str(uuid4())
        token = AuthService.create_jwt_token(
            user,
            tenant_id=tenant_id,
            tenant_role="member"
        )
        
        tenant_info = AuthService.get_tenant_from_token(token)
        
        assert tenant_info is not None
        assert tenant_info["tenant_id"] == tenant_id
        assert tenant_info["tenant_role"] == "member"

    def test_get_tenant_from_token_without_tenant(self, db):
        """从没有租户信息的 token 提取返回 None"""
        user = User(
            id=uuid4(),
            username=f"no_extract_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="noextract@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_jwt_token(user)  # 无租户信息
        tenant_info = AuthService.get_tenant_from_token(token)
        
        assert tenant_info is None


class TestTenantContext:
    """TenantContext 测试"""

    def test_set_and_get(self):
        """设置和获取租户上下文"""
        # 初始为空
        assert TenantContext.get_current() is None
        assert TenantContext.get_tenant_id() is None
        
        # 设置上下文
        TenantContext.set(tenant_id="tenant-123", tenant_role="admin")
        
        ctx = TenantContext.get_current()
        assert ctx is not None
        assert ctx["tenant_id"] == "tenant-123"
        assert ctx["tenant_role"] == "admin"
        assert TenantContext.get_tenant_id() == "tenant-123"
        assert TenantContext.get_tenant_role() == "admin"
        
        # 清除
        TenantContext.clear()
        assert TenantContext.get_current() is None

    def test_get_tenant_role_default(self):
        """默认角色为 member"""
        TenantContext.set(tenant_id="tenant-123")
        assert TenantContext.get_tenant_role() == "member"
        TenantContext.clear()


class TestTenantDependencies:
    """FastAPI 依赖测试"""

    def test_get_tenant_context_with_valid_token(self, db):
        """有效 token 返回租户上下文（同步方式测试）"""
        import asyncio
        
        user = User(
            id=uuid4(),
            username=f"dep_test_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="dep@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        tenant_id = str(uuid4())
        token = AuthService.create_jwt_token(
            user,
            tenant_id=tenant_id,
            tenant_role="admin"
        )
        
        # 模拟请求
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
        request = Request(scope)
        
        # 运行异步函数
        result = asyncio.run(get_tenant_context(request))
        
        assert result is not None
        assert result["tenant_id"] == tenant_id
        assert result["tenant_role"] == "admin"

    def test_get_tenant_context_without_auth(self):
        """无认证返回 None"""
        import asyncio
        
        scope = {
            "type": "http",
            "headers": [],
        }
        request = Request(scope)
        
        result = asyncio.run(get_tenant_context(request))
        assert result is None

    def test_get_tenant_context_without_tenant(self, db):
        """有认证但无租户信息返回 None"""
        import asyncio
        
        user = User(
            id=uuid4(),
            username=f"no_tenant_dep_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="notenantdep@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_jwt_token(user)  # 无租户信息
        
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
        request = Request(scope)
        
        result = asyncio.run(get_tenant_context(request))
        assert result is None

    def test_require_tenant_raises_without_tenant(self):
        """require_tenant 无租户时抛出异常"""
        import asyncio
        
        scope = {
            "type": "http",
            "headers": [],
        }
        request = Request(scope)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_tenant(request))
        
        assert exc_info.value.status_code == 403
