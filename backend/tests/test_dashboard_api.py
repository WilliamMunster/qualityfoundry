"""Dashboard API Unit Tests

6 个测试：
1. test_dashboard_summary_401_no_token - 无 token 返回 401
2. test_dashboard_summary_viewer_can_access - VIEWER 有 OrchestrationRead 权限可访问（无 audit_summary）
3. test_dashboard_summary_success_admin - ADMIN 成功并返回 audit_summary
4. test_dashboard_summary_success_user - USER 成功（无 audit_summary）
5. test_dashboard_summary_trend_missing_fields - trend 缺字段容错
6. test_dashboard_summary_recent_runs_contract - recent_runs 字段契约
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from qualityfoundry.main import app
from qualityfoundry.api.deps.auth_deps import get_current_user
from qualityfoundry.database.user_models import User, UserRole


@pytest.fixture
def client():
    return TestClient(app)


def create_mock_user(role: UserRole, username: str = "mock_user") -> User:
    """创建 mock 用户对象"""
    return User(
        id=uuid4(),
        username=username,
        password_hash="mock_hash",
        email=f"{username}@test.com",
        full_name=f"Mock {role.value}",
        role=role,
        is_active=True,
    )


class TestDashboardSummaryAuth:
    """权限相关测试"""
    
    def test_dashboard_summary_401_no_token(self, client):
        """无 token 返回 401"""
        # 临时移除默认 mock，模拟无认证场景
        original_override = app.dependency_overrides.get(get_current_user)
        
        # 设置为抛出异常
        def no_auth():
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="未认证")
        
        app.dependency_overrides[get_current_user] = no_auth
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        finally:
            if original_override:
                app.dependency_overrides[get_current_user] = original_override
            else:
                app.dependency_overrides.pop(get_current_user, None)
    
    def test_dashboard_summary_viewer_can_access(self, client):
        """VIEWER 有 OrchestrationRead 权限可访问（无 audit_summary）"""
        mock_viewer = create_mock_user(UserRole.VIEWER, "test_viewer_dash")
        app.dependency_overrides[get_current_user] = lambda: mock_viewer
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            # VIEWER 有 ORCHESTRATION_READ 权限，可以访问
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "cards" in data
            # VIEWER 不是 ADMIN，不应该有 audit_summary
            assert data["audit_summary"] is None
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user


class TestDashboardSummarySuccess:
    """成功场景测试"""
    
    def test_dashboard_summary_success_admin(self, client):
        """ADMIN 成功并返回 audit_summary"""
        mock_admin = create_mock_user(UserRole.ADMIN, "test_admin_dash")
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # 验证返回结构
            assert "cards" in data
            assert "trend" in data
            assert "recent_runs" in data
            assert "audit_summary" in data
            
            # ADMIN 应该有 audit_summary
            assert data["audit_summary"] is not None
            assert "total_events" in data["audit_summary"]
            assert "runs_with_events" in data["audit_summary"]
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_dashboard_summary_success_user(self, client):
        """USER 成功（无 audit_summary，因为 USER != ADMIN）"""
        mock_user = create_mock_user(UserRole.USER, "test_user_dash")
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # 验证返回结构完整
            assert "cards" in data
            cards = data["cards"]
            assert cards["pass_count"] >= 0
            assert cards["fail_count"] >= 0
            assert cards["hitl_count"] >= 0
            assert cards["total_runs"] >= 0
            
            assert isinstance(data["trend"], list)
            assert isinstance(data["recent_runs"], list)
            
            # USER 不是 ADMIN，不应该有 audit_summary
            assert data["audit_summary"] is None
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user


class TestDashboardSummaryContract:
    """契约测试"""
    
    def test_dashboard_summary_trend_missing_fields(self, client):
        """trend 缺字段时容错（elapsed_ms 可为 null）"""
        mock_admin = create_mock_user(UserRole.ADMIN, "test_admin_trend")
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # trend 中每个点应有基础字段
            for point in data["trend"]:
                assert "run_id" in point
                assert "started_at" in point
                # elapsed_ms 可为 null
                assert "elapsed_ms" in point  # 字段存在即可
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_dashboard_summary_recent_runs_contract(self, client):
        """recent_runs 字段契约验证"""
        mock_admin = create_mock_user(UserRole.ADMIN, "test_admin_contract")
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # recent_runs 中每项应有必需字段
            for run in data["recent_runs"]:
                assert "run_id" in run
                assert "started_at" in run
                assert "decision" in run
                assert "tool_count" in run
                # 可选字段存在即可
                assert "policy_version" in run
                assert "policy_hash" in run
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
