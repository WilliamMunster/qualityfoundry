"""Tests for Audit Log (PR-C)

验证审计日志的写入与查询功能。
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qualityfoundry.database.config import Base
from qualityfoundry.database.audit_log_models import AuditEventType, AuditLog
from qualityfoundry.services.audit_service import (
    audit_event_to_dict,
    is_audit_enabled,
    query_audit_events,
    write_audit_event,
)


@pytest.fixture
def db_session():
    """创建独立的数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestAuditLogModel:
    """AuditLog 模型测试"""

    def test_create_audit_log(self, db_session):
        """可以创建审计日志记录"""
        log = AuditLog(
            run_id=uuid4(),
            event_type=AuditEventType.TOOL_STARTED,
            tool_name="run_pytest",
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.ts is not None

    def test_event_types(self):
        """事件类型枚举值正确"""
        assert AuditEventType.TOOL_STARTED.value == "tool_started"
        assert AuditEventType.TOOL_FINISHED.value == "tool_finished"
        assert AuditEventType.DECISION_MADE.value == "decision_made"
        assert AuditEventType.POLICY_BLOCKED.value == "policy_blocked"


class TestAuditService:
    """审计服务测试"""

    def test_write_audit_event(self, db_session):
        """可以写入审计事件"""
        run_id = uuid4()
        log = write_audit_event(
            db_session,
            run_id=run_id,
            event_type=AuditEventType.TOOL_STARTED,
            tool_name="run_pytest",
            args={"test_path": "tests/"},
        )

        assert log is not None
        assert log.run_id == run_id
        assert log.tool_name == "run_pytest"
        assert log.args_hash is not None

    def test_write_audit_event_with_status(self, db_session):
        """可以写入带状态的审计事件"""
        run_id = uuid4()
        log = write_audit_event(
            db_session,
            run_id=run_id,
            event_type=AuditEventType.TOOL_FINISHED,
            tool_name="run_pytest",
            status="success",
            duration_ms=1234,
        )

        assert log.status == "success"
        assert log.duration_ms == 1234

    def test_write_audit_event_with_decision(self, db_session):
        """可以写入决策事件"""
        run_id = uuid4()
        log = write_audit_event(
            db_session,
            run_id=run_id,
            event_type=AuditEventType.DECISION_MADE,
            decision_source="gate_evaluation",
            details={"decision": "PASS", "reason": "all tests passed"},
        )

        assert log.decision_source == "gate_evaluation"
        assert log.details is not None

    def test_query_audit_events(self, db_session):
        """可以查询审计事件"""
        run_id = uuid4()

        # 写入多个事件
        write_audit_event(
            db_session,
            run_id=run_id,
            event_type=AuditEventType.TOOL_STARTED,
            tool_name="run_pytest",
        )
        write_audit_event(
            db_session,
            run_id=run_id,
            event_type=AuditEventType.TOOL_FINISHED,
            tool_name="run_pytest",
            status="success",
        )

        events = query_audit_events(db_session, run_id)

        assert len(events) == 2
        assert events[0].event_type == AuditEventType.TOOL_STARTED
        assert events[1].event_type == AuditEventType.TOOL_FINISHED

    def test_query_audit_events_empty(self, db_session):
        """无事件时返回空列表"""
        events = query_audit_events(db_session, uuid4())
        assert events == []

    def test_audit_event_to_dict(self, db_session):
        """可以序列化审计事件"""
        run_id = uuid4()
        log = write_audit_event(
            db_session,
            run_id=run_id,
            event_type=AuditEventType.TOOL_STARTED,
            tool_name="run_pytest",
        )

        d = audit_event_to_dict(log)

        assert d["run_id"] == str(run_id)
        assert d["event_type"] == "tool_started"
        assert d["tool_name"] == "run_pytest"
        assert "ts" in d


class TestFeatureFlag:
    """Feature flag 测试"""

    def test_audit_enabled_default(self):
        """默认启用审计"""
        # 清除环境变量
        os.environ.pop("AUDIT_LOG_ENABLED", None)
        assert is_audit_enabled() is True

    def test_audit_disabled_by_env(self):
        """可以通过环境变量禁用"""
        os.environ["AUDIT_LOG_ENABLED"] = "false"
        try:
            assert is_audit_enabled() is False
        finally:
            os.environ.pop("AUDIT_LOG_ENABLED", None)

    def test_write_skipped_when_disabled(self, db_session):
        """禁用时跳过写入"""
        os.environ["AUDIT_LOG_ENABLED"] = "false"
        try:
            log = write_audit_event(
                db_session,
                run_id=uuid4(),
                event_type=AuditEventType.TOOL_STARTED,
            )
            assert log is None
        finally:
            os.environ.pop("AUDIT_LOG_ENABLED", None)


class TestAuditAPI:
    """审计 API 测试"""

    def test_get_audit_events_empty(self, client):
        """查询无事件的运行"""
        run_id = uuid4()
        response = client.get(f"/api/v1/audit/{run_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == str(run_id)
        assert data["events"] == []
        assert data["count"] == 0
        assert data["audit_enabled"] is True


class TestRunsListAPI:
    """Runs 列表 API 测试"""

    def test_list_runs_empty(self, client):
        """无运行记录时返回空列表"""
        response = client.get("/api/v1/orchestrations/runs")

        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["count"] == 0
        assert data["total"] == 0

    def test_list_runs_pagination(self, client):
        """分页参数生效"""
        response = client.get("/api/v1/orchestrations/runs?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert "count" in data
        assert "total" in data
