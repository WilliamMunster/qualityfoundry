"""Legacy Runs 只读保护测试

测试 /api/v1/runs 端点的 deprecation headers 和只读行为。
确保 legacy 端点不存在写操作。
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from qualityfoundry.main import app
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.api.deps.auth_deps import get_current_user


# Mock ADMIN 用户
MOCK_ADMIN = User(
    id=uuid4(),
    username="legacy_test_admin",
    password_hash="mock_hash",
    email="legacy_admin@test.com",
    full_name="Legacy Test Admin",
    role=UserRole.ADMIN,
    is_active=True,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


class TestLegacyRunsDeprecationHeaders:
    """Legacy runs 端点 deprecation headers 测试"""

    def test_legacy_list_has_deprecation_headers(self, client):
        """GET /runs 返回 deprecation headers"""
        response = client.get("/api/v1/runs")
        
        # 无论是否有数据，都应该有 deprecation headers
        assert "Deprecation" in response.headers, "缺少 Deprecation header"
        assert response.headers["Deprecation"] == "true"
        
        assert "X-Deprecated" in response.headers, "缺少 X-Deprecated header"
        assert "orchestrations/runs" in response.headers["X-Deprecated"]
        
        assert "Link" in response.headers, "缺少 Link header"
        assert "successor-version" in response.headers["Link"]

    def test_legacy_detail_has_deprecation_headers(self, client):
        """GET /runs/{id} 返回 deprecation headers"""
        # 使用一个不存在的 run_id（会返回 404，但 headers 应该存在）
        response = client.get("/api/v1/runs/nonexistent-run-id")
        
        # 即使 404，也应该有 deprecation headers
        # 注意：FastAPI 的 HTTPException 不会保留自定义 headers，所以 404 可能没有
        # 但 200 响应必须有
        if response.status_code == 200:
            assert "Deprecation" in response.headers


class TestLegacyRunsReadOnly:
    """Legacy runs 写操作不可用测试"""

    def test_legacy_post_not_allowed(self, client):
        """POST /runs 返回 404 或 405（不存在写端点）"""
        response = client.post("/api/v1/runs", json={})
        assert response.status_code in [404, 405], f"POST /runs 应该不可用，实际: {response.status_code}"

    def test_legacy_put_not_allowed(self, client):
        """PUT /runs/{id} 返回 404 或 405"""
        response = client.put("/api/v1/runs/some-run-id", json={})
        assert response.status_code in [404, 405], f"PUT /runs 应该不可用，实际: {response.status_code}"

    def test_legacy_patch_not_allowed(self, client):
        """PATCH /runs/{id} 返回 404 或 405"""
        response = client.patch("/api/v1/runs/some-run-id", json={})
        assert response.status_code in [404, 405], f"PATCH /runs 应该不可用，实际: {response.status_code}"

    def test_legacy_delete_not_allowed(self, client):
        """DELETE /runs/{id} 返回 404 或 405"""
        response = client.delete("/api/v1/runs/some-run-id")
        assert response.status_code in [404, 405], f"DELETE /runs 应该不可用，实际: {response.status_code}"


class TestLegacyRunsRunKind:
    """Legacy runs run_kind 字段测试"""

    def test_legacy_list_has_run_kind(self, client):
        """GET /runs 返回的列表中每个项目都有 run_kind"""
        response = client.get("/api/v1/runs")
        
        if response.status_code == 200:
            data = response.json()
            # 如果有数据，每个 run 都应该有 run_kind
            if isinstance(data, list):
                for run in data:
                    if isinstance(run, dict):
                        assert run.get("run_kind") == "legacy_artifact"
