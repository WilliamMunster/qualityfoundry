"""
执行管理 API 单元测试
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


def test_create_execution():
    """测试创建执行"""
    # 创建需求、场景、用例、环境
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
    
    testcase_response = client.post(
        "/api/v1/testcases",
        json={
            "scenario_id": scenario_id,
            "title": "测试用例",
            "steps": ["步骤1"]
        }
    )
    testcase_id = testcase_response.json()["id"]
    
    env_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    environment_id = env_response.json()["id"]
    
    # 创建执行
    response = client.post(
        "/api/v1/executions",
        json={
            "testcase_id": testcase_id,
            "environment_id": environment_id,
            "mode": "dsl"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["testcase_id"] == testcase_id
    assert data["environment_id"] == environment_id
    assert data["mode"] == "dsl"
    assert data["status"] == "pending"


def test_list_executions():
    """测试执行列表"""
    # 创建测试数据
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
    
    testcase_response = client.post(
        "/api/v1/testcases",
        json={
            "scenario_id": scenario_id,
            "title": "测试用例",
            "steps": ["步骤1"]
        }
    )
    testcase_id = testcase_response.json()["id"]
    
    env_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    environment_id = env_response.json()["id"]
    
    # 创建多个执行
    for i in range(3):
        client.post(
            "/api/v1/executions",
            json={
                "testcase_id": testcase_id,
                "environment_id": environment_id,
                "mode": "dsl"
            }
        )
    
    # 获取列表
    response = client.get("/api/v1/executions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


def test_get_execution():
    """测试获取执行详情"""
    # 创建测试数据
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
    
    testcase_response = client.post(
        "/api/v1/testcases",
        json={
            "scenario_id": scenario_id,
            "title": "测试用例",
            "steps": ["步骤1"]
        }
    )
    testcase_id = testcase_response.json()["id"]
    
    env_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    environment_id = env_response.json()["id"]
    
    # 创建执行
    create_response = client.post(
        "/api/v1/executions",
        json={
            "testcase_id": testcase_id,
            "environment_id": environment_id,
            "mode": "dsl"
        }
    )
    execution_id = create_response.json()["id"]
    
    # 获取详情
    response = client.get(f"/api/v1/executions/{execution_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == execution_id


def test_get_execution_status():
    """测试获取执行状态"""
    # 创建测试数据
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
    
    testcase_response = client.post(
        "/api/v1/testcases",
        json={
            "scenario_id": scenario_id,
            "title": "测试用例",
            "steps": ["步骤1"]
        }
    )
    testcase_id = testcase_response.json()["id"]
    
    env_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    environment_id = env_response.json()["id"]
    
    # 创建执行
    create_response = client.post(
        "/api/v1/executions",
        json={
            "testcase_id": testcase_id,
            "environment_id": environment_id,
            "mode": "dsl"
        }
    )
    execution_id = create_response.json()["id"]
    
    # 获取状态
    response = client.get(f"/api/v1/executions/{execution_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == execution_id
    assert "status" in data
