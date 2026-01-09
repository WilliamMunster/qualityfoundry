"""
审核流程 API 单元测试
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import Base
from qualityfoundry.main import app

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前创建表，测试后删除表"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_approval():
    """测试创建审核"""
    # 先创建需求和场景
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    scenario_response = client.post(
        "/api/v1/scenarios",
        json={
            "requirement_id": requirement_id,
            "title": "测试场景",
            "steps": ["步骤1"]
        }
    )
    scenario_id = scenario_response.json()["id"]
    
    # 创建审核
    response = client.post(
        "/api/v1/approvals",
        json={
            "entity_type": "scenario",
            "entity_id": scenario_id,
            "reviewer": "test_reviewer"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["entity_type"] == "scenario"
    assert data["status"] == "pending"


def test_approve_approval():
    """测试批准审核"""
    # 创建需求、场景和审核
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    scenario_response = client.post(
        "/api/v1/scenarios",
        json={
            "requirement_id": requirement_id,
            "title": "测试场景",
            "steps": ["步骤1"]
        }
    )
    scenario_id = scenario_response.json()["id"]
    
    approval_response = client.post(
        "/api/v1/approvals",
        json={
            "entity_type": "scenario",
            "entity_id": scenario_id
        }
    )
    approval_id = approval_response.json()["id"]
    
    # 批准审核
    response = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={
            "reviewer": "approver",
            "review_comment": "批准通过"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["reviewer"] == "approver"
    assert data["review_comment"] == "批准通过"


def test_reject_approval():
    """测试拒绝审核"""
    # 创建需求、场景和审核
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    scenario_response = client.post(
        "/api/v1/scenarios",
        json={
            "requirement_id": requirement_id,
            "title": "测试场景",
            "steps": ["步骤1"]
        }
    )
    scenario_id = scenario_response.json()["id"]
    
    approval_response = client.post(
        "/api/v1/approvals",
        json={
            "entity_type": "scenario",
            "entity_id": scenario_id
        }
    )
    approval_id = approval_response.json()["id"]
    
    # 拒绝审核
    response = client.post(
        f"/api/v1/approvals/{approval_id}/reject",
        json={
            "reviewer": "rejector",
            "review_comment": "需要修改"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["reviewer"] == "rejector"


def test_list_approvals():
    """测试审核列表"""
    # 创建多个审核
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    for i in range(3):
        scenario_response = client.post(
            "/api/v1/scenarios",
            json={
                "requirement_id": requirement_id,
                "title": f"场景{i}",
                "steps": ["步骤1"]
            }
        )
        scenario_id = scenario_response.json()["id"]
        
        client.post(
            "/api/v1/approvals",
            json={
                "entity_type": "scenario",
                "entity_id": scenario_id
            }
        )
    
    # 获取列表
    response = client.get("/api/v1/approvals")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
