"""
系统集成测试

使用 conftest.py 中统一的测试数据库配置
注意：这些测试需要完整的数据库和服务环境，在 CI 中可能会跳过
"""
import os
import pytest
from fastapi.testclient import TestClient

from qualityfoundry.main import app

# 检测是否在 CI 环境中运行
IN_CI = os.environ.get("CI", "").lower() == "true" or os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

# 使用 conftest.py 中的 setup_database fixture（autouse=True）
client = TestClient(app)


@pytest.mark.skip(reason="需要真实 AI 服务配置，暂时跳过")
def test_full_workflow():
    """
    测试完整工作流：
    需求 → 场景 → 用例 → 环境 → 执行
    """
    # 1. 创建需求
    req_response = client.post(
        "/api/v1/requirements",
        json={
            "title": "用户登录功能",
            "content": "实现用户登录功能，包括用户名密码验证",
            "version": "v1.0"
        }
    )
    assert req_response.status_code == 201
    requirement = req_response.json()
    requirement_id = requirement["id"]
    
    # 2. 生成场景
    scenario_response = client.post(
        "/api/v1/scenarios/generate",
        json={
            "requirement_id": requirement_id,
            "auto_approve": False
        }
    )
    assert scenario_response.status_code == 201
    scenarios = scenario_response.json()
    assert len(scenarios) > 0
    scenario_id = scenarios[0]["id"]
    
    # 3. 审核场景
    approve_response = client.post(
        f"/api/v1/scenarios/{scenario_id}/approve",
        json={
            "reviewer": "test_reviewer",
            "comment": "场景合理"
        }
    )
    assert approve_response.status_code == 200
    
    # 4. 生成用例
    testcase_response = client.post(
        "/api/v1/testcases/generate",
        json={
            "scenario_id": scenario_id,
            "auto_approve": False
        }
    )
    assert testcase_response.status_code == 201
    testcases = testcase_response.json()
    assert len(testcases) > 0
    testcase_id = testcases[0]["id"]
    
    # 5. 审核用例
    approve_tc_response = client.post(
        f"/api/v1/testcases/{testcase_id}/approve",
        json={
            "reviewer": "test_reviewer",
            "comment": "用例完整"
        }
    )
    assert approve_tc_response.status_code == 200
    
    # 6. 创建环境
    env_response = client.post(
        "/api/v1/environments",
        json={
            "name": "test",
            "base_url": "http://localhost:3000",
            "variables": {"API_KEY": "test_key"}
        }
    )
    assert env_response.status_code == 201
    environment_id = env_response.json()["id"]
    
    # 7. 触发执行
    exec_response = client.post(
        "/api/v1/executions",
        json={
            "testcase_id": testcase_id,
            "environment_id": environment_id,
            "mode": "dsl"
        }
    )
    assert exec_response.status_code == 201
    execution = exec_response.json()
    assert execution["status"] == "pending"
    
    # 8. 查询执行状态
    status_response = client.get(f"/api/v1/executions/{execution['id']}/status")
    assert status_response.status_code == 200


@pytest.mark.skip(reason="需要完整数据库环境，暂时跳过")
def test_approval_workflow():
    """测试审核流程"""
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
    
    # 查询审核列表
    approvals_response = client.get("/api/v1/approvals")
    assert approvals_response.status_code == 200
    
    # 批准场景
    approve_response = client.post(
        f"/api/v1/scenarios/{scenario_id}/approve",
        json={"reviewer": "reviewer1"}
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["approval_status"] == "approved"


@pytest.mark.skip(reason="需要完整数据库环境，暂时跳过")
def test_environment_health_check():
    """测试环境健康检查"""
    # 创建环境
    env_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:8000",
            "health_check_url": "http://localhost:8000/health"
        }
    )
    environment_id = env_response.json()["id"]
    
    # 健康检查（可能失败，因为服务未运行）
    health_response = client.post(f"/api/v1/environments/{environment_id}/health-check")
    assert health_response.status_code == 200
    assert "is_healthy" in health_response.json()
