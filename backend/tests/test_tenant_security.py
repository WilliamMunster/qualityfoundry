"""租户安全测试 (F003)

补充缺失的安全测试场景
"""
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from qualityfoundry.database.tenant_models import TenantMembership, TenantRole
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.api.deps.auth_deps import get_current_user
from qualityfoundry.database.config import get_db
from qualityfoundry.main import app
from qualityfoundry.services.tenant_service import TenantService
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


class TestF003SecurityScenarios:
    """F003 安全测试场景"""

    def test_f003a_admin_cannot_delete_tenant(self, db):
        """F003a: admin 不能删除租户（只有 owner 可以）"""
        # 创建 owner
        owner = create_test_user(db, "delete_owner")
        
        # 创建 admin 用户
        admin_user = create_test_user(db, "delete_admin")
        
        # owner 创建租户
        owner_client = get_client_with_user(owner)
        response = owner_client.post(
            "/api/v1/tenants",
            json={"slug": "delete-test", "name": "Delete Test"},
        )
        tenant_id = UUID(response.json()["id"])
        
        # 将 admin_user 添加为 admin 角色
        TenantService.add_member(db, tenant_id, admin_user.id, TenantRole.ADMIN)
        
        # admin 尝试删除租户
        admin_client = get_client_with_user(admin_user)
        response = admin_client.delete(f"/api/v1/tenants/{tenant_id}")
        
        assert response.status_code == 403
        assert "需要所有者权限" in response.json()["detail"]

    def test_f003b_member_cannot_add_members(self, db):
        """F003b: member 不能添加成员（只有 admin/owner 可以）"""
        # 创建 owner 和 member
        owner = create_test_user(db, "add_owner")
        member = create_test_user(db, "add_member_user")
        new_user = create_test_user(db, "new_guy")
        
        # owner 创建租户
        owner_client = get_client_with_user(owner)
        response = owner_client.post(
            "/api/v1/tenants",
            json={"slug": "member-add-test", "name": "Member Add Test"},
        )
        tenant_id = UUID(response.json()["id"])
        
        # 将 member 添加为 member 角色
        TenantService.add_member(db, tenant_id, member.id, TenantRole.MEMBER)
        
        # member 尝试添加新成员
        member_client = get_client_with_user(member)
        response = member_client.post(
            f"/api/v1/tenants/{tenant_id}/members",
            json={"user_id": str(new_user.id), "role": "member"},
        )
        
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]

    def test_f003c_add_nonexistent_user_id(self, db):
        """F003c: 添加不存在的 user_id 返回 400"""
        # 创建 owner
        owner = create_test_user(db, "exist_owner")
        
        # owner 创建租户
        owner_client = get_client_with_user(owner)
        response = owner_client.post(
            "/api/v1/tenants",
            json={"slug": "exist-test", "name": "Exist Test"},
        )
        tenant_id = response.json()["id"]
        
        # 尝试添加不存在的用户
        fake_user_id = str(uuid4())
        response = owner_client.post(
            f"/api/v1/tenants/{tenant_id}/members",
            json={"user_id": fake_user_id, "role": "member"},
        )
        
        assert response.status_code == 400
        assert "用户不存在" in response.json()["detail"]

    def test_f003d_admin_add_owner_blocked(self, db):
        """F003d: admin 添加 owner 角色被阻止"""
        # 创建 owner 和 admin
        owner = create_test_user(db, "block_owner")
        admin_user = create_test_user(db, "block_admin")
        target_user = create_test_user(db, "target_user")
        
        # owner 创建租户
        owner_client = get_client_with_user(owner)
        response = owner_client.post(
            "/api/v1/tenants",
            json={"slug": "block-test", "name": "Block Test"},
        )
        tenant_id = UUID(response.json()["id"])
        
        # 将 admin_user 添加为 admin 角色
        TenantService.add_member(db, tenant_id, admin_user.id, TenantRole.ADMIN)
        
        # admin 尝试添加 owner 角色
        admin_client = get_client_with_user(admin_user)
        response = admin_client.post(
            f"/api/v1/tenants/{tenant_id}/members",
            json={"user_id": str(target_user.id), "role": "owner"},
        )
        
        assert response.status_code == 400
        assert "不能直接添加所有者角色" in response.json()["detail"]

    def test_f003e_delete_tenant_cascades_memberships(self, db):
        """F003e: 删除租户级联删除成员关系"""
        # 创建 owner 和多个成员
        owner = create_test_user(db, "cascade_owner")
        member1 = create_test_user(db, "cascade_member1")
        member2 = create_test_user(db, "cascade_member2")
        
        # owner 创建租户
        owner_client = get_client_with_user(owner)
        response = owner_client.post(
            "/api/v1/tenants",
            json={"slug": "cascade-test", "name": "Cascade Test"},
        )
        tenant_id_str = response.json()["id"]
        tenant_id = UUID(tenant_id_str)
        
        # 添加成员
        TenantService.add_member(db, tenant_id, member1.id, TenantRole.MEMBER)
        TenantService.add_member(db, tenant_id, member2.id, TenantRole.MEMBER)
        
        # 验证成员存在
        memberships_before = db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id
        ).all()
        assert len(memberships_before) == 3  # owner + 2 members
        
        # 删除租户
        response = owner_client.delete(f"/api/v1/tenants/{tenant_id_str}")
        assert response.status_code == 204
        
        # 验证成员关系也被删除
        memberships_after = db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id
        ).all()
        assert len(memberships_after) == 0
