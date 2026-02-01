"""租户 API 集成测试

测试 /api/v1/tenants 端点
"""
from uuid import uuid4
from fastapi.testclient import TestClient

from qualityfoundry.database.tenant_models import Tenant, TenantMembership, TenantRole, TenantStatus
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.api.deps.auth_deps import get_current_user
from qualityfoundry.database.config import get_db
from qualityfoundry.main import app
from tests.conftest import TestingSessionLocal


def create_test_user(db, username, role=UserRole.USER):
    """创建测试用户"""
    user = User(
        id=uuid4(),
        username=username,
        password_hash="test_hash",
        email=f"{username}@test.com",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def override_get_db_for_test():
    """为测试提供数据库会话"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def get_client_with_user(user):
    """获取使用指定用户的测试客户端"""
    def override_get_current_user():
        return user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db_for_test
    
    client = TestClient(app)
    return client


class TestTenantAPICreate:
    """创建租户 API 测试"""

    def test_create_tenant_success(self, db):
        """成功创建租户"""
        # 创建用户
        user = create_test_user(db, "tenant_creator")
        client = get_client_with_user(user)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "slug": "test-tenant",
                "name": "Test Tenant",
                "description": "A test tenant",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "test-tenant"
        assert data["name"] == "Test Tenant"
        assert data["status"] == "active"

    def test_create_tenant_duplicate_slug(self, db):
        """重复的 slug 返回 400"""
        user = create_test_user(db, "dup_user")
        client = get_client_with_user(user)
        
        # 第一个租户
        client.post(
            "/api/v1/tenants",
            json={"slug": "dup-tenant", "name": "First"},
        )
        
        # 重复创建
        response = client.post(
            "/api/v1/tenants",
            json={"slug": "dup-tenant", "name": "Second"},
        )
        
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]

    def test_create_tenant_unauthorized(self):
        """未认证返回 401"""
        # 清除认证覆盖
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[get_db] = override_get_db_for_test
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={"slug": "test", "name": "Test"},
        )
        assert response.status_code == 401


class TestTenantAPIList:
    """列出租户 API 测试"""

    def test_list_my_tenants(self, db):
        """列出当前用户的租户"""
        user = create_test_user(db, "list_user")
        
        # 创建租户
        tenant = Tenant(
            id=uuid4(),
            slug="list-tenant",
            name="List Tenant",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        db.flush()
        
        # 添加成员关系
        membership = TenantMembership(
            tenant_id=tenant.id,
            user_id=user.id,
            role=TenantRole.MEMBER,
        )
        db.add(membership)
        db.commit()
        
        client = get_client_with_user(user)
        response = client.get("/api/v1/tenants")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    def test_get_my_tenants(self, db):
        """获取我的租户列表（专用端点）"""
        user = create_test_user(db, "my_tenants_user")
        client = get_client_with_user(user)
        
        # 先创建租户
        client.post(
            "/api/v1/tenants",
            json={"slug": "my-tenant", "name": "My Tenant"},
        )
        
        response = client.get("/api/v1/tenants/my")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTenantAPIDetail:
    """租户详情 API 测试"""

    def test_get_tenant_detail(self, db):
        """获取租户详情"""
        user = create_test_user(db, "detail_user")
        client = get_client_with_user(user)
        
        # 创建租户
        response = client.post(
            "/api/v1/tenants",
            json={"slug": "detail-tenant", "name": "Detail Tenant"},
        )
        tenant_id = response.json()["id"]
        
        # 获取详情
        response = client.get(f"/api/v1/tenants/{tenant_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "detail-tenant"

    def test_get_nonexistent_tenant(self, db):
        """获取不存在的租户返回 404"""
        user = create_test_user(db, "notfound_user")
        client = get_client_with_user(user)
        
        response = client.get(f"/api/v1/tenants/{uuid4()}")
        
        assert response.status_code == 404


class TestTenantAPIUpdate:
    """更新租户 API 测试"""

    def test_update_tenant(self, db):
        """更新租户信息"""
        user = create_test_user(db, "update_user")
        client = get_client_with_user(user)
        
        # 创建租户（用户自动成为 owner）
        response = client.post(
            "/api/v1/tenants",
            json={"slug": "update-tenant", "name": "Original Name"},
        )
        tenant_id = response.json()["id"]
        
        # 更新
        response = client.put(
            f"/api/v1/tenants/{tenant_id}",
            json={"name": "Updated Name", "description": "New description"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"


class TestTenantAPIMembers:
    """成员管理 API 测试"""

    def test_list_members(self, db):
        """列出成员"""
        user = create_test_user(db, "member_list_owner")
        client = get_client_with_user(user)
        
        # 创建租户
        response = client.post(
            "/api/v1/tenants",
            json={"slug": "member-list", "name": "Member List"},
        )
        tenant_id = response.json()["id"]
        
        # 列出成员
        response = client.get(f"/api/v1/tenants/{tenant_id}/members")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # 至少包含所有者

    def test_add_member(self, db):
        """添加成员"""
        # 所有者
        owner = create_test_user(db, "add_member_owner")
        
        # 新成员
        new_user = create_test_user(db, "new_member")
        
        client = get_client_with_user(owner)
        
        # 创建租户
        response = client.post(
            "/api/v1/tenants",
            json={"slug": "add-member", "name": "Add Member"},
        )
        tenant_id = response.json()["id"]
        
        # 添加成员
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/members",
            json={"user_id": str(new_user.id), "role": "member"},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(new_user.id)
        assert data["role"] == "member"

    def test_remove_member(self, db):
        """移除成员"""
        # 所有者
        owner = create_test_user(db, "remove_owner")
        
        # 要移除的成员
        member = create_test_user(db, "to_remove")
        
        client = get_client_with_user(owner)
        
        # 创建租户
        response = client.post(
            "/api/v1/tenants",
            json={"slug": "remove-member", "name": "Remove Member"},
        )
        tenant_id = response.json()["id"]
        
        # 先添加成员
        client.post(
            f"/api/v1/tenants/{tenant_id}/members",
            json={"user_id": str(member.id), "role": "member"},
        )
        
        # 移除成员
        response = client.delete(f"/api/v1/tenants/{tenant_id}/members/{member.id}")
        
        assert response.status_code == 204


class TestTenantAPIPermissions:
    """权限测试"""

    def test_non_member_cannot_access(self, db):
        """非成员无法访问租户"""
        # 创建者
        owner = create_test_user(db, "private_owner")
        
        # 创建租户
        owner_client = get_client_with_user(owner)
        response = owner_client.post(
            "/api/v1/tenants",
            json={"slug": "private-tenant", "name": "Private"},
        )
        tenant_id = response.json()["id"]
        
        # 非成员尝试访问
        outsider = create_test_user(db, "outsider")
        outsider_client = get_client_with_user(outsider)
        
        response = outsider_client.get(f"/api/v1/tenants/{tenant_id}")
        
        assert response.status_code == 403
