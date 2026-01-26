"""Dashboard Summary API Contract Tests

覆盖：days 参数、limit 参数、字段存在、统计一致性。
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


def create_mock_admin() -> User:
    """创建 mock ADMIN 用户"""
    return User(
        id=uuid4(),
        username="contract_test_admin",
        password_hash="mock_hash",
        email="contract_admin@test.com",
        full_name="Contract Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )


class TestDashboardSummaryContract:
    """Dashboard Summary API 契约测试"""
    
    def test_days_param_default_7(self, client):
        """默认 days=7 返回成功"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            assert "cards" in data
            assert "trend" in data
            assert "recent_runs" in data
            assert "by_decision" in data
            assert "by_policy_hash" in data
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_days_param_30(self, client):
        """days=30 合法参数返回成功"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary?days=30")
            assert resp.status_code == 200
            data = resp.json()
            assert "cards" in data
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_days_param_90(self, client):
        """days=90 合法参数返回成功"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary?days=90")
            assert resp.status_code == 200
            data = resp.json()
            assert "cards" in data
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_days_param_out_of_range(self, client):
        """days=100 超出范围返回 422"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary?days=100")
            assert resp.status_code == 422
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_limit_param_default_50(self, client):
        """默认 limit=50 返回成功"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            # recent_runs 最多 10 条
            assert len(data["recent_runs"]) <= 10
            # trend 最多 20 条
            assert len(data["trend"]) <= 20
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_limit_param_max_200(self, client):
        """limit=200 合法最大值返回成功"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary?limit=200")
            assert resp.status_code == 200
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_limit_param_over_max(self, client):
        """limit=300 超出最大值返回 422"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary?limit=300")
            assert resp.status_code == 422
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_field_existence(self, client):
        """所有必需字段存在"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # cards 字段
            cards = data["cards"]
            assert "pass_count" in cards
            assert "fail_count" in cards
            assert "hitl_count" in cards
            assert "avg_elapsed_ms" in cards
            assert "short_circuit_count" in cards
            assert "total_runs" in cards
            
            # 新增聚合字段
            assert isinstance(data["by_decision"], dict)
            assert isinstance(data["by_policy_hash"], dict)
            
            # trend 结构
            for point in data["trend"]:
                assert "run_id" in point
                assert "started_at" in point
                assert "elapsed_ms" in point
            
            # recent_runs 结构
            for run in data["recent_runs"]:
                assert "run_id" in run
                assert "started_at" in run
                assert "decision" in run
                assert "tool_count" in run
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_counts_consistency(self, client):
        """统计一致性：pass + fail + hitl <= total_runs"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            cards = data["cards"]
            
            # 有决策的 run 数不超过总数
            decision_sum = cards["pass_count"] + cards["fail_count"] + cards["hitl_count"]
            assert decision_sum <= cards["total_runs"]
            
            # by_decision 计数和应等于 decision_sum
            by_decision_sum = sum(data["by_decision"].values())
            assert by_decision_sum == decision_sum
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_timeseries_field_exists(self, client):
        """timeseries 字段存在"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # timeseries 字段存在且是列表
            assert "timeseries" in data
            assert isinstance(data["timeseries"], list)
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_timeseries_point_structure(self, client):
        """timeseries 数据点结构正确"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # timeseries 中每个点应有必需字段
            for point in data["timeseries"]:
                assert "date" in point
                assert "pass_count" in point
                assert "fail_count" in point
                assert "need_hitl_count" in point
                assert "total" in point
                # date 格式应为 YYYY-MM-DD
                assert len(point["date"]) == 10
                assert point["date"][4] == "-" and point["date"][7] == "-"
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user
    
    def test_timeseries_sum_consistency(self, client):
        """timeseries 各天总和 <= total_runs"""
        mock_admin = create_mock_admin()
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        try:
            resp = client.get("/api/v1/dashboard/summary")
            assert resp.status_code == 200
            data = resp.json()
            
            # timeseries 各天总和不超过 total_runs
            timeseries_total = sum(p["total"] for p in data["timeseries"])
            assert timeseries_total <= data["cards"]["total_runs"]
            
            # 每天的 pass + fail + need_hitl <= total
            for point in data["timeseries"]:
                decision_sum = point["pass_count"] + point["fail_count"] + point["need_hitl_count"]
                assert decision_sum <= point["total"]
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user

