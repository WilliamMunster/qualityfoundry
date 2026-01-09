"""
场景管理 API 单元测试
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


def test_generate_scenarios():
    """测试 AI 生成场景"""
    # 先创建需求
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    # 生成场景
    response = client.post(
        "/api/v1/scenarios/generate",
        json={
            "requirement_id": requirement_id,
            "auto_approve": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) > 0
    assert data[0]["approval_status"] == "approved"


def test_create_scenario():
    """测试创建场景"""
    # 先创建需求
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    # 创建场景
    response = client.post(
        "/api/v1/scenarios",
        json={
            "requirement_id": requirement_id,
            "title": "测试场景",
            "description": "测试描述",
            "steps": ["步骤1", "步骤2"]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "测试场景"
    assert len(data["steps"]) == 2


def test_list_scenarios():
    """测试场景列表"""
    # 创建需求和场景
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    for i in range(3):
        client.post(
            "/api/v1/scenarios",
            json={
                "requirement_id": requirement_id,
                "title": f"场景{i}",
                "steps": ["步骤1"]
            }
        )
    
    # 获取列表
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


def test_get_scenario():
    """测试获取场景详情"""
    # 创建需求和场景
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
    
    # 获取详情
    response = client.get(f"/api/v1/scenarios/{scenario_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == scenario_id


def test_update_scenario():
    """测试更新场景"""
    # 创建需求和场景
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    scenario_response = client.post(
        "/api/v1/scenarios",
        json={
            "requirement_id": requirement_id,
            "title": "原标题",
            "steps": ["步骤1"]
        }
    )
    scenario_id = scenario_response.json()["id"]
    
    # 更新场景
    response = client.put(
        f"/api/v1/scenarios/{scenario_id}",
        json={
            "title": "新标题",
            "steps": ["新步骤1", "新步骤2"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "新标题"
    assert len(data["steps"]) == 2


def test_delete_scenario():
    """测试删除场景"""
    # 创建需求和场景
    req_response = client.post(
        "/api/v1/requirements",
        json={"title": "测试需求", "content": "内容", "version": "v1.0"}
    )
    requirement_id = req_response.json()["id"]
    
    scenario_response = client.post(
        "/api/v1/scenarios",
        json={
            "requirement_id": requirement_id,
            "title": "待删除场景",
            "steps": ["步骤1"]
        }
    )
    scenario_id = scenario_response.json()["id"]
    
    # 删除场景
    response = client.delete(f"/api/v1/scenarios/{scenario_id}")
    assert response.status_code == 204
    
    # 验证已删除
    get_response = client.get(f"/api/v1/scenarios/{scenario_id}")
    assert get_response.status_code == 404
