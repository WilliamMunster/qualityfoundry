"""
用例管理 API 单元测试

使用 conftest.py 中统一的测试数据库配置
"""
import os
import pytest
from fastapi.testclient import TestClient

from qualityfoundry.main import app

# 不再使用模块级全局 client，改为使用 conftest.py 提供的 client fixture

ENABLE_AI_TESTS = os.environ.get("QF_ENABLE_AI_TESTS", "").lower() in ("1", "true", "yes")
AI_API_KEY = os.environ.get("QF_AI_API_KEY")
AI_BASE_URL = os.environ.get("QF_AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.environ.get("QF_AI_MODEL", "gpt-4o-mini")
AI_PROVIDER = os.environ.get("QF_AI_PROVIDER", "openai")
AI_READY = ENABLE_AI_TESTS and bool(AI_API_KEY)


def _ensure_ai_config(client):
    response = client.post(
        "/api/v1/ai-configs",
        json={
            "name": "测试 AI 配置",
            "provider": AI_PROVIDER,
            "model": AI_MODEL,
            "api_key": AI_API_KEY,
            "base_url": AI_BASE_URL,
            "assigned_steps": ["testcase_generation"],
            "is_default": True,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.skipif(not AI_READY, reason="需要真实 AI 服务配置（QF_ENABLE_AI_TESTS=1 且 QF_AI_API_KEY 已配置）")
def test_generate_testcases(client):
    """测试 AI 生成用例"""
    _ensure_ai_config(client)
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
    
    # 生成用例
    response = client.post(
        "/api/v1/testcases/generate",
        json={
            "scenario_id": scenario_id,
            "auto_approve": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) > 0
    assert data[0]["approval_status"] == "approved"


def test_create_testcase(client):
    """测试创建用例"""
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
    
    # 创建用例
    response = client.post(
        "/api/v1/testcases",
        json={
            "scenario_id": scenario_id,
            "title": "测试用例",
            "preconditions": ["前置条件1"],
            "steps": [{"step": "步骤1", "expected": "预期结果1"}, {"step": "步骤2", "expected": "预期结果2"}],
            "expected_results": ["预期结果1", "预期结果2"]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "测试用例"
    assert len(data["steps"]) == 2


def test_list_testcases(client):
    """测试用例列表"""
    # 创建需求、场景和用例
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
    
    for i in range(3):
        client.post(
            "/api/v1/testcases",
            json={
                "scenario_id": scenario_id,
                "title": f"用例{i}",
                "steps": [{"step": "步骤1", "expected": "预期结果1"}]
            }
        )
    
    # 获取列表
    response = client.get("/api/v1/testcases")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


def test_update_testcase(client):
    """测试更新用例"""
    # 创建需求、场景和用例
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
            "title": "原标题",
            "steps": [{"step": "步骤1", "expected": "预期结果1"}]
        }
    )
    testcase_id = testcase_response.json()["id"]
    
    # 更新用例
    response = client.put(
        f"/api/v1/testcases/{testcase_id}",
        json={
            "title": "新标题",
            "steps": [{"step": "新步骤1", "expected": "新预期1"}, {"step": "新步骤2", "expected": "新预期2"}]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "新标题"
    assert len(data["steps"]) == 2


def test_delete_testcase(client):
    """测试删除用例"""
    # 创建需求、场景和用例
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
            "title": "待删除用例",
            "steps": [{"step": "步骤1", "expected": "预期结果1"}]
        }
    )
    testcase_id = testcase_response.json()["id"]
    
    # 删除用例
    response = client.delete(f"/api/v1/testcases/{testcase_id}")
    assert response.status_code == 204
    
    # 验证已删除
    get_response = client.get(f"/api/v1/testcases/{testcase_id}")
    assert get_response.status_code == 404
