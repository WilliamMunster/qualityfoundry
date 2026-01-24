"""API 契约测试：RunDetail DTO

确保 RunDetail 响应结构稳定，防止字段命名漂移。
此测试作为 CI 护栏，任何字段变更都需要同步更新此契约。

Contract Snapshot: v1.0 (2026-01-24)
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from qualityfoundry.main import app
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.api.deps.auth_deps import get_current_user


# Mock 用户
MOCK_ADMIN = User(
    id=uuid4(),
    username="contract_admin",
    password_hash="mock_hash",
    email="contract@test.com",
    full_name="Contract Admin",
    role=UserRole.ADMIN,
    is_active=True,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


class TestRunsListContract:
    """GET /api/v1/orchestrations/runs 响应契约"""

    # 必须存在的字段
    REQUIRED_FIELDS = {"run_id", "started_at", "finished_at", "decision", "tool_count"}

    def test_runs_list_response_structure(self, client):
        """列表响应必须包含 runs/count/total"""
        response = client.get("/api/v1/orchestrations/runs")
        assert response.status_code == 200
        
        data = response.json()
        assert "runs" in data, "响应缺少 'runs' 字段"
        assert "count" in data, "响应缺少 'count' 字段"
        assert "total" in data, "响应缺少 'total' 字段"
        
        assert isinstance(data["runs"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["total"], int)

    def test_run_summary_fields(self, client):
        """每个 run 摘要必须包含必需字段"""
        response = client.get("/api/v1/orchestrations/runs?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        for run in data["runs"]:
            for field in self.REQUIRED_FIELDS:
                assert field in run, f"run 摘要缺少必需字段: {field}"


class TestRunDetailContract:
    """GET /api/v1/orchestrations/runs/{id} 响应契约"""

    # 顶层必须存在的块
    REQUIRED_TOP_BLOCKS = {"run_id", "owner", "summary", "policy", "repro", "governance", "artifacts"}
    
    # repro 块必须存在的字段（防止字段命名漂移）
    REPRO_EXPECTED_FIELDS = {"git_sha", "branch", "dirty", "deps_fingerprint"}
    
    # summary 块必须存在的字段
    SUMMARY_EXPECTED_FIELDS = {"started_at", "finished_at", "ok", "decision", "decision_source", "tool_count"}
    
    # policy 块必须存在的字段
    POLICY_EXPECTED_FIELDS = {"version", "hash"}
    
    # artifacts 数组中每个元素必须存在的字段
    ARTIFACT_EXPECTED_FIELDS = {"type", "path"}

    def test_run_detail_top_level_blocks(self, client):
        """RunDetail 必须包含所有顶层块"""
        # 先获取一个真实的 run_id
        list_resp = client.get("/api/v1/orchestrations/runs?limit=1")
        if list_resp.status_code != 200 or not list_resp.json()["runs"]:
            pytest.skip("无可用的 run 记录用于测试")
        
        run_id = list_resp.json()["runs"][0]["run_id"]
        
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
        assert response.status_code == 200
        
        data = response.json()
        for block in self.REQUIRED_TOP_BLOCKS:
            assert block in data, f"RunDetail 缺少顶层块: {block}"

    def test_run_detail_summary_fields(self, client):
        """summary 块必须包含所有必需字段"""
        list_resp = client.get("/api/v1/orchestrations/runs?limit=1")
        if list_resp.status_code != 200 or not list_resp.json()["runs"]:
            pytest.skip("无可用的 run 记录用于测试")
        
        run_id = list_resp.json()["runs"][0]["run_id"]
        
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
        assert response.status_code == 200
        
        summary = response.json().get("summary", {})
        for field in self.SUMMARY_EXPECTED_FIELDS:
            assert field in summary, f"summary 块缺少字段: {field}"

    def test_run_detail_repro_fields(self, client):
        """repro 块字段命名契约（防止 git_branch vs branch 漂移）"""
        list_resp = client.get("/api/v1/orchestrations/runs?limit=1")
        if list_resp.status_code != 200 or not list_resp.json()["runs"]:
            pytest.skip("无可用的 run 记录用于测试")
        
        run_id = list_resp.json()["runs"][0]["run_id"]
        
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
        assert response.status_code == 200
        
        repro = response.json().get("repro")
        if repro is not None:  # repro 可能为 null（无 evidence）
            for field in self.REPRO_EXPECTED_FIELDS:
                assert field in repro, (
                    f"repro 块缺少字段: {field}。"
                    f"检查是否存在字段命名漂移（如 git_branch vs branch）"
                )

    def test_run_detail_policy_fields(self, client):
        """policy 块必须包含版本和哈希"""
        list_resp = client.get("/api/v1/orchestrations/runs?limit=1")
        if list_resp.status_code != 200 or not list_resp.json()["runs"]:
            pytest.skip("无可用的 run 记录用于测试")
        
        run_id = list_resp.json()["runs"][0]["run_id"]
        
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
        assert response.status_code == 200
        
        policy = response.json().get("policy")
        if policy is not None:
            for field in self.POLICY_EXPECTED_FIELDS:
                assert field in policy, f"policy 块缺少字段: {field}"

    def test_run_detail_artifacts_structure(self, client):
        """artifacts 数组元素必须包含 type 和 path"""
        list_resp = client.get("/api/v1/orchestrations/runs?limit=1")
        if list_resp.status_code != 200 or not list_resp.json()["runs"]:
            pytest.skip("无可用的 run 记录用于测试")
        
        run_id = list_resp.json()["runs"][0]["run_id"]
        
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
        assert response.status_code == 200
        
        artifacts = response.json().get("artifacts", [])
        for i, artifact in enumerate(artifacts):
            for field in self.ARTIFACT_EXPECTED_FIELDS:
                assert field in artifact, f"artifacts[{i}] 缺少字段: {field}"

    def test_run_detail_audit_summary_admin_only(self, client):
        """ADMIN 用户应该能看到 audit_summary"""
        list_resp = client.get("/api/v1/orchestrations/runs?limit=1")
        if list_resp.status_code != 200 or not list_resp.json()["runs"]:
            pytest.skip("无可用的 run 记录用于测试")
        
        run_id = list_resp.json()["runs"][0]["run_id"]
        
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
        assert response.status_code == 200
        
        # ADMIN 应该有 audit_summary（可以是 null，但字段必须存在）
        assert "audit_summary" in response.json(), "ADMIN 响应缺少 audit_summary 字段"


class TestPoliciesCurrentContract:
    """GET /api/v1/policies/current 响应契约"""

    REQUIRED_FIELDS = {"version", "policy_hash", "git_sha", "source", "summary"}

    def test_policies_current_response(self, client):
        """policies/current 必须返回策略元信息"""
        response = client.get("/api/v1/policies/current")
        assert response.status_code == 200
        
        data = response.json()
        for field in self.REQUIRED_FIELDS:
            assert field in data, f"policies/current 缺少字段: {field}"
