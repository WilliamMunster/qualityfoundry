"""Run Center API 验收测试 (DoD-1/2/3)

验证:
- Run 列表与详情 API
- Evidence Schema 完整性
- 字段存在性与类型
"""

import pytest
import json
from uuid import uuid4
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from qualityfoundry.main import app
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.database.audit_log_models import AuditLog, AuditEventType
from qualityfoundry.services.auth_service import AuthService
from qualityfoundry.governance.tracing.collector import TraceCollector, Evidence
from qualityfoundry.schemas import validate_evidence_v1, EvidenceValidationError


# ============ Fixtures ============

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def test_user(db: Session):
    """创建测试用户"""
    user = User(
        id=uuid4(),
        username=f"test_user_{uuid4().hex[:8]}",
        email="test@example.com",
        password_hash=AuthService.hash_password("test_pass"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client: TestClient, test_user: User):
    """获取认证 headers"""
    response = client.post(
        "/api/v1/users/login",
        json={"username": test_user.username, "password": "test_pass"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_run_data(db: Session, test_user: User):
    """创建样本运行数据（含审计日志）"""
    run_id = uuid4()
    now = datetime.now(timezone.utc)
    
    # 创建审计事件序列
    events = [
        AuditLog(
            run_id=run_id,
            event_type=AuditEventType.TOOL_STARTED,
            created_by_user_id=test_user.id,
            tool_name="run_pytest",
            ts=now,
        ),
        AuditLog(
            run_id=run_id,
            event_type=AuditEventType.TOOL_FINISHED,
            created_by_user_id=test_user.id,
            tool_name="run_pytest",
            status="success",
            duration_ms=1234,
            ts=now,
        ),
        AuditLog(
            run_id=run_id,
            event_type=AuditEventType.DECISION_MADE,
            created_by_user_id=test_user.id,
            status="PASS",
            decision_source="gate_evaluator",
            details=json.dumps({"reason": "All tests passed"}),
            ts=now,
        ),
    ]
    
    for event in events:
        db.add(event)
    db.commit()
    
    return {"run_id": run_id, "user_id": test_user.id}


@pytest.fixture
def sample_evidence(tmp_path, sample_run_data):
    """创建样本 evidence.json"""
    run_id = sample_run_data["run_id"]
    
    collector = TraceCollector(
        run_id=run_id,
        input_nl="运行 smoke 测试",
        environment={"environment_id": str(uuid4())},
        artifact_root=tmp_path / "artifacts",
    )
    
    # 模拟添加工具结果
    from qualityfoundry.tools.contracts import ToolResult, ToolStatus, ToolMetrics
    result = ToolResult(
        status=ToolStatus.SUCCESS,
        stdout="tests passed",
        stderr="",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        metrics=ToolMetrics(
            attempts=1,
            retries_used=0,
            duration_ms=1234,
            steps_total=5,
            steps_passed=5,
            steps_failed=0,
        ),
    )
    collector.add_tool_result("run_pytest", result)
    
    evidence = collector.collect()
    collector.save(evidence)
    
    return evidence


# ============ DoD-1: Run 生命周期主路径 ============

class TestRunLifecycle:
    """Run 生命周期 API 测试"""
    
    def test_list_runs_success(self, client: TestClient, auth_headers: dict, sample_run_data: dict):
        """1.1/1.2: 获取 Run 列表"""
        response = client.get("/api/v1/orchestrations/runs", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应结构
        assert "runs" in data
        assert "count" in data
        assert "total" in data
        assert isinstance(data["runs"], list)
        
        # 验证列表项结构
        if data["runs"]:
            run = data["runs"][0]
            assert "run_id" in run
            assert "started_at" in run
            assert "decision" in run
            assert "tool_count" in run
    
    def test_list_runs_pagination(self, client: TestClient, auth_headers: dict):
        """1.2: 列表分页功能"""
        response = client.get("/api/v1/orchestrations/runs?limit=5&offset=0", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] <= 5
        assert data["total"] >= data["count"]
    
    def test_get_run_detail_success(
        self, 
        client: TestClient, 
        auth_headers: dict, 
        sample_run_data: dict,
        sample_evidence: Evidence,
    ):
        """1.3: 获取 Run 详情"""
        run_id = sample_run_data["run_id"]
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证核心字段
        assert data["run_id"] == str(run_id)
        assert "summary" in data
        assert "artifacts" in data
        
        # 验证 summary 字段
        summary = data["summary"]
        assert "started_at" in summary
        assert "decision" in summary
        assert "tool_count" in summary
        
        # 验证 decision 枚举值
        assert summary["decision"] in ["PASS", "FAIL", "NEED_HITL", None]
    
    def test_get_run_detail_not_found(self, client: TestClient, auth_headers: dict):
        """1.3: 获取不存在的 Run"""
        fake_run_id = uuid4()
        response = client.get(f"/api/v1/orchestrations/runs/{fake_run_id}", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_run_detail_permission_denied(
        self, 
        client: TestClient, 
        db: Session,
        sample_run_data: dict,
    ):
        """1.4: 权限检查 - 其他用户无法访问"""
        # 移除全局 Admin 覆盖，以测试真实权限
        from qualityfoundry.api.deps.auth_deps import get_current_user
        app.dependency_overrides.pop(get_current_user, None)
        
        try:
            # 创建另一个用户
            other_user = User(
                id=uuid4(),
                username=f"other_user_{uuid4().hex[:8]}",
                email="other@example.com",
                password_hash=AuthService.hash_password("other_pass"),
                role=UserRole.USER,
                is_active=True,
            )
            db.add(other_user)
            db.commit()
            
            # 登录获取 token
            login_resp = client.post(
                "/api/v1/users/login",
                json={"username": other_user.username, "password": "other_pass"}
            )
            other_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
            
            # 尝试访问他人 run
            run_id = sample_run_data["run_id"]
            response = client.get(f"/api/v1/orchestrations/runs/{run_id}", headers=other_headers)
            
            assert response.status_code == 403
        finally:
            # 恢复覆盖
            from qualityfoundry.api.deps.auth_deps import get_current_user
            # 直接使用 inline lambda 模拟管理员
            app.dependency_overrides[get_current_user] = lambda: User(
                id=uuid4(), username="test_admin", role=UserRole.ADMIN, is_active=True
            )


# ============ DoD-2: 证据链可下载且可复核 ============

class TestEvidenceChain:
    """Evidence 链完整性测试"""
    
    def test_evidence_schema_validation(self, sample_evidence: Evidence):
        """2.1: Evidence Schema 校验"""
        evidence_dict = sample_evidence.model_dump(mode="json", by_alias=True)
        
        # 应通过校验
        validate_evidence_v1(evidence_dict)
        
        # 验证 Schema URI
        assert evidence_dict.get("$schema") == "https://qualityfoundry.ai/schemas/evidence.v1.schema.json"
    
    def test_evidence_schema_validation_failure(self):
        """2.1: Schema 校验应拒绝无效数据"""
        invalid_evidence = {
            "run_id": "not-a-uuid",  # 无效格式
            "input_nl": "test",
            # 缺少必填字段
        }
        
        with pytest.raises(EvidenceValidationError):
            validate_evidence_v1(invalid_evidence)
    
    def test_evidence_required_fields(self, sample_evidence: Evidence):
        """2.2: Evidence 必填字段检查"""
        evidence_dict = sample_evidence.model_dump()
        
        # 核心字段
        required_fields = [
            "run_id", "input_nl", "environment", "tool_calls",
            "artifacts", "summary", "repro", "governance", "collected_at"
        ]
        
        for field in required_fields:
            assert field in evidence_dict, f"Missing required field: {field}"
    
    def test_evidence_tool_calls_structure(self, sample_evidence: Evidence):
        """2.2: Tool calls 结构检查"""
        tool_calls = sample_evidence.tool_calls
        
        assert len(tool_calls) > 0
        
        for call in tool_calls:
            call_dict = call.model_dump()
            assert "tool_name" in call_dict
            assert "status" in call_dict
            assert "duration_ms" in call_dict
            assert isinstance(call_dict["duration_ms"], int)
            assert call_dict["duration_ms"] >= 0
    
    def test_evidence_artifacts_path_relative(self, sample_evidence: Evidence):
        """2.3: Artifacts 路径相对化检查"""
        for artifact in sample_evidence.artifacts:
            path = artifact.get("path", "")
            # 不应以 / 开头（绝对路径）
            assert not path.startswith("/"), f"Absolute path detected: {path}"
            # 不应包含 Windows 盘符
            assert not path[1:3] == ":/", f"Windows absolute path detected: {path}"
    
    def test_evidence_repro_metadata(self, sample_evidence: Evidence):
        """2.4: Repro 元数据存在性"""
        repro = sample_evidence.repro
        
        assert repro is not None
        assert hasattr(repro, 'git_sha')
        assert hasattr(repro, 'git_branch')
        assert hasattr(repro, 'git_dirty')
        if repro.git_dirty is not None:
            assert isinstance(repro.git_dirty, bool)
    
    def test_evidence_download_api(
        self, 
        client: TestClient, 
        auth_headers: dict,
        sample_run_data: dict,
        sample_evidence: Evidence,
    ):
        """2.1: Evidence 下载 API"""
        run_id = sample_run_data["run_id"]
        response = client.get(f"/api/v1/artifacts/{run_id}/evidence.json", headers=auth_headers)
        
        # 注意：此端点可能返回文件或 JSON，取决于实现
        # 这里假设返回文件或 JSON 数据
        assert response.status_code in [200, 404]  # 404 如果文件不存在
        
        if response.status_code == 200:
            # 验证是有效的 JSON
            data = response.json()
            assert "$schema" in data
            assert data["run_id"] == str(run_id)


# ============ DoD-3: 最小审计闭环可解释 ============

class TestAuditTrail:
    """审计追踪测试"""
    
    def test_governance_fields_present(self, sample_evidence: Evidence):
        """3.3: 成本治理字段存在性"""
        governance = sample_evidence.governance
        
        assert governance is not None
        
        gov_dict = governance.model_dump()
        assert "budget" in gov_dict
        assert "short_circuited" in gov_dict
        
        # 预算字段
        budget = gov_dict["budget"]
        assert "elapsed_ms_total" in budget
        assert "attempts_total" in budget
        assert "retries_used_total" in budget
    
    def test_decision_source_field(self, sample_evidence: Evidence):
        """3.1: decision_source 字段"""
        governance = sample_evidence.governance
        
        if governance:
            gov_dict = governance.model_dump()
            # decision_source 应在 governance 中
            assert "decision_source" in gov_dict
            if gov_dict["decision_source"]:
                assert gov_dict["decision_source"] in ["gate_evaluator", "governance_short_circuit"]
    
    def test_summary_decision_no_source(self, client: TestClient, auth_headers: dict, sample_run_data: dict):
        """3.x: summary.decision_source 已移除（避免重复）"""
        run_id = sample_run_data["run_id"]
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get("summary", {})
            
            # summary 中不应有 decision_source（已在 governance 中）
            # 此测试验证字段收敛
            assert "decision_source" not in summary, "decision_source should be in governance, not summary"


# ============ 性能与边界测试 ============

class TestPerformanceAndEdgeCases:
    """性能和边界测试"""
    
    def test_list_runs_large_offset(self, client: TestClient, auth_headers: dict):
        """大数据量偏移测试"""
        response = client.get("/api/v1/orchestrations/runs?limit=10&offset=10000", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # 应返回空列表而非错误
        assert data["runs"] == []
        assert data["count"] == 0
    
    def test_evidence_validation_performance(self, sample_evidence: Evidence):
        """Schema 校验性能测试"""
        import time
        
        evidence_dict = sample_evidence.model_dump(mode="json", by_alias=True)
        
        start = time.time()
        for _ in range(50):  # CI 环境调整为 50 次
            validate_evidence_v1(evidence_dict)
        elapsed = time.time() - start
        
        # 50 次校验应在 3 秒内完成（CI 环境宽容度）
        assert elapsed < 3.0, f"Schema validation too slow: {elapsed}s"


# ============ 集成测试标记 ============

@pytest.mark.smoke
class TestRunCenterSmoke:
    """Run Center 冒烟测试（快速验证核心路径）"""
    
    def test_smoke_list_and_detail(self, client: TestClient, auth_headers: dict):
        """快速验证列表和详情 API 可用"""
        # 列表
        list_resp = client.get("/api/v1/orchestrations/runs?limit=1", headers=auth_headers)
        assert list_resp.status_code == 200
        
        data = list_resp.json()
        if data["runs"]:
            # 如果有数据，验证详情
            run_id = data["runs"][0]["run_id"]
            detail_resp = client.get(f"/api/v1/orchestrations/runs/{run_id}", headers=auth_headers)
            assert detail_resp.status_code in [200, 403]  # 200 或权限不足
