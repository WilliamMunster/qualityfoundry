import pytest
import json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from qualityfoundry.main import app
from qualityfoundry.database.audit_log_models import AuditLog, AuditEventType
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.api.deps.auth_deps import get_current_user

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    """提供数据库会话"""
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# 移除冲突的 shared_setup，交由 conftest.py 的 apply_overrides 自动处理

@pytest.fixture
def admin_user(db_session: Session):
    """确保 admin 用户在数据库中并返回"""
    user = User(username="admin_contract", role=UserRole.ADMIN, password_hash="mock")
    db_session.add(user)
    db_session.commit()
    return user

def test_run_detail_has_artifact_audit_nullable(client: TestClient, db_session: Session, admin_user: User):
    """验证没有审计事件时，字段为 null"""
    run_id = uuid4()
    # 模拟一个没有审计数据的任务（但需要有一条初始记录通过 get_run_detail 的初检）
    event = AuditLog(
        run_id=run_id,
        event_type=AuditEventType.TOOL_STARTED,
        tool_name="test_tool",
        status="started",
        created_by_user_id=admin_user.id
    )
    db_session.add(event)
    db_session.commit()

    # 模拟登录
    app.dependency_overrides[get_current_user] = lambda: admin_user
    response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    # 验证字段存在且为 None (JSON 中的 null)
    assert "artifact_audit" in data
    assert data["artifact_audit"] is None

def test_run_detail_artifact_audit_structure(client: TestClient, db_session: Session, admin_user: User):
    """验证包含审计事件时，结构正确"""
    run_id = uuid4()
    details = {
        "tool_name": "run_pytest",
        "total_count": 5,
        "stats_by_type": {"screenshot": 2, "log": 3},
        "samples": [{"path": "s1.png", "type": "screenshot"}],
        "truncated": False,
        "boundary": {"scope": ["tests"], "extensions": [".png"]}
    }
    
    # 写入初始事件和产物审计事件
    db_session.add(AuditLog(
        run_id=run_id,
        event_type=AuditEventType.TOOL_STARTED,
        tool_name="run_pytest",
        created_by_user_id=admin_user.id
    ))
    db_session.add(AuditLog(
        run_id=run_id,
        event_type=AuditEventType.ARTIFACT_COLLECTED,
        tool_name="run_pytest",
        details=json.dumps(details),
        created_by_user_id=admin_user.id
    ))
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: admin_user
    response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    audit = data["artifact_audit"]
    
    assert audit is not None
    assert audit["total_count"] == 5
    assert audit["stats_by_type"] == {"screenshot": 2, "log": 3}
    assert audit["truncated"] is False
    assert audit["boundary"]["scope"] == ["tests"]
    assert len(audit["samples"]) == 1

def test_run_detail_artifact_audit_last_win(client: TestClient, db_session: Session, admin_user: User):
    """(P0.5) 验证多条 ARTIFACT_COLLECTED 记录时，API 返回最新的一条"""
    run_id = uuid4()
    
    # 第一条（旧）
    db_session.add(AuditLog(
        run_id=run_id,
        event_type=AuditEventType.ARTIFACT_COLLECTED,
        details=json.dumps({
            "total_count": 1, 
            "note": "old",
            "stats_by_type": {"log": 1},
            "truncated": False,
            "boundary": {"scope": [], "extensions": []}
        }),
        created_by_user_id=admin_user.id
    ))
    db_session.commit()
    
    # 第二条（新）
    db_session.add(AuditLog(
        run_id=run_id,
        event_type=AuditEventType.ARTIFACT_COLLECTED,
        details=json.dumps({
            "total_count": 2, 
            "note": "new",
            "stats_by_type": {"log": 2},
            "truncated": False,
            "boundary": {"scope": [], "extensions": []}
        }),
        created_by_user_id=admin_user.id
    ))
    db_session.commit()

    # 模拟登录
    app.dependency_overrides[get_current_user] = lambda: admin_user
    response = client.get(f"/api/v1/orchestrations/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["artifact_audit"]["total_count"] == 2
    # 由 autouse fixture 自动处理清理逻辑

def test_run_detail_artifact_audit_rbac(client: TestClient, db_session: Session, admin_user: User):
    """(P0.5) 验证 RBAC 权限一致性：非 Owner 且非 Admin 访问他人的 run 应被拒或无法获取审计字段"""
    # 场景：User A 创建了 Run，User B 尝试访问
    user_a = User(username="user_a", role=UserRole.VIEWER, password_hash="mock")
    user_b = User(username="user_b", role=UserRole.VIEWER, password_hash="mock")
    db_session.add(user_a)
    db_session.add(user_b)
    db_session.commit()

    run_id = uuid4()
    # 增加基础事件以确保 Run 记录在逻辑上存在
    db_session.add(AuditLog(
        run_id=run_id,
        event_type=AuditEventType.TOOL_STARTED,
        details=json.dumps({"msg": "init"}),
        created_by_user_id=user_a.id
    ))
    db_session.add(AuditLog(
        run_id=run_id,
        event_type=AuditEventType.ARTIFACT_COLLECTED,
        details=json.dumps({
            "total_count": 10,
            "stats_by_type": {"log": 10},
            "truncated": False,
            "boundary": {"scope": [], "extensions": []}
        }),
        created_by_user_id=user_a.id
    ))
    db_session.commit()

    # User B 访问 User A 的 Run
    app.dependency_overrides[get_current_user] = lambda: user_b
    response = client.get(f"/api/v1/orchestrations/runs/{run_id}")

    # 应该返回 403 Forbidden
    assert response.status_code == 403
    # 由 autouse fixture 自动处理清理逻辑
