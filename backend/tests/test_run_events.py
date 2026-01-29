"""Run Events & SSE Tests."""
import pytest
import json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from qualityfoundry.main import app
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.services.event_service import EventService
from qualityfoundry.services.auth_service import AuthService

@pytest.fixture
def auth_headers(db: Session):
    """获取管理员 token"""
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            id=uuid4(),
            username="admin",
            email="admin@test.com",
            password_hash=AuthService.hash_password("admin"),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(user)
    token = AuthService.create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}

def test_event_service_emit_and_get(db: Session):
    """测试事件发布与检索"""
    service = EventService(db)
    run_id = uuid4()
    
    # 1. 发布事件
    event1 = service.emit_event(run_id, "test.event", {"foo": "bar"})
    assert event1.event_type == "test.event"
    assert json.loads(event1.data)["foo"] == "bar"
    
    # 2. 检索事件
    events = service.get_events(run_id)
    assert len(events) == 1
    assert events[0].id == event1.id
    
    # 3. Last-Event-ID 补发
    event2 = service.emit_event(run_id, "test.next")
    events_since = service.get_events(run_id, last_event_id=str(event1.id))
    assert len(events_since) == 1
    assert events_since[0].id == event2.id

def test_sse_endpoint_structure(db: Session):
    """测试 SSE 端点结构响应"""
    client = TestClient(app)
    run_id = uuid4()
    
    # 模拟管理员登录（这里简化，直接使用 RequireOrchestrationRead 的 mock）
    from qualityfoundry.api.deps.auth_deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: User(
        id=uuid4(), 
        username="admin", 
        role=UserRole.ADMIN, 
        is_active=True
    )
    
    try:
        # 发布一个事件
        service = EventService(db)
        service.emit_event(run_id, "run.started")
        
        # 模拟运行结束，以便 generator 退出
        from qualityfoundry.database.audit_log_models import AuditLog, AuditEventType
        db.add(AuditLog(run_id=run_id, event_type=AuditEventType.DECISION_MADE, status="PASS"))
        db.commit()
        
        # 请求 SSE
        response = client.get(f"/api/v1/orchestrations/runs/{run_id}/events")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # 验证包含事件内容
        assert "event: run.started" in response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)
