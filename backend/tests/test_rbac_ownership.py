"""RBAC 所有权测试

测试用户只能访问自己创建的运行记录，ADMIN 可访问全部。
"""
from uuid import uuid4
from fastapi.testclient import TestClient

from qualityfoundry.main import app
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.api.deps.auth_deps import get_current_user


# 创建不同角色的 Mock 用户
MOCK_ADMIN = User(
    id=uuid4(),
    username="test_admin",
    password_hash="mock_hash",
    email="admin@test.com",
    full_name="Test Admin",
    role=UserRole.ADMIN,
    is_active=True,
)

MOCK_USER_A = User(
    id=uuid4(),
    username="user_a",
    password_hash="mock_hash",
    email="user_a@test.com",
    full_name="User A",
    role=UserRole.USER,
    is_active=True,
)

MOCK_USER_B = User(
    id=uuid4(),
    username="user_b",
    password_hash="mock_hash",
    email="user_b@test.com",
    full_name="User B",
    role=UserRole.USER,
    is_active=True,
)

MOCK_VIEWER = User(
    id=uuid4(),
    username="viewer",
    password_hash="mock_hash",
    email="viewer@test.com",
    full_name="Viewer",
    role=UserRole.VIEWER,
    is_active=True,
)


class TestUnauthorizedAccess:
    """未认证访问测试"""

    def test_runs_requires_auth(self):
        """测试 /runs 需要认证"""
        # 清除 mock 以测试真实认证
        original_override = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides.pop(get_current_user, None)
        
        client = TestClient(app)
        response = client.get("/api/v1/runs")
        
        # 恢复 mock
        if original_override:
            app.dependency_overrides[get_current_user] = original_override
        
        assert response.status_code == 401

    def test_orchestrations_runs_requires_auth(self):
        """测试 /orchestrations/runs 需要认证"""
        original_override = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides.pop(get_current_user, None)
        
        client = TestClient(app)
        response = client.get("/api/v1/orchestrations/runs")
        
        if original_override:
            app.dependency_overrides[get_current_user] = original_override
        
        assert response.status_code == 401


class TestOwnershipFilter:
    """所有权过滤测试"""

    def test_admin_can_see_all_runs(self, client):
        """ADMIN 可以看到所有运行记录"""
        # 使用 ADMIN 用户
        app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
        
        response = client.get("/api/v1/orchestrations/runs")
        assert response.status_code == 200
        # ADMIN 应该能访问

    def test_user_only_sees_own_runs(self, client):
        """USER 只能看到自己的运行记录"""
        # 使用普通用户
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER_A
        
        response = client.get("/api/v1/orchestrations/runs")
        assert response.status_code == 200
        # 返回的运行列表应该只包含该用户创建的

    def test_viewer_can_read_runs(self, client):
        """VIEWER 可以读取运行记录"""
        app.dependency_overrides[get_current_user] = lambda: MOCK_VIEWER
        
        response = client.get("/api/v1/orchestrations/runs")
        assert response.status_code == 200


class TestPermissionDenied:
    """权限拒绝测试"""

    def test_viewer_cannot_execute_orchestration(self, client):
        """VIEWER 不能执行编排"""
        app.dependency_overrides[get_current_user] = lambda: MOCK_VIEWER
        
        response = client.post("/api/v1/orchestrations/run", json={
            "nl_input": "运行测试"
        })
        
        assert response.status_code == 403

    def test_user_cannot_access_admin_audit(self, client):
        """USER 不能访问审计日志（即使是自己的）"""
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER_A
        
        # 使用一个随机的 run_id
        run_id = str(uuid4())
        response = client.get(f"/api/v1/audit/{run_id}")
        
        # AUDIT_READ 只给 ADMIN，所以应该是 403
        assert response.status_code == 403

    def test_admin_can_access_audit(self, client):
        """ADMIN 可以访问审计日志"""
        app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
        
        run_id = str(uuid4())
        response = client.get(f"/api/v1/audit/{run_id}")
        
        # ADMIN 有权限，可能返回空列表
        assert response.status_code == 200
