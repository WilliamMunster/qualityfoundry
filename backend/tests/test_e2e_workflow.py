"""
端到端全流程测试

测试完整的业务流程：需求 → 场景 → 用例 → 执行 → 报告
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
def test_complete_workflow_end_to_end():
    """
    完整端到端测试：
    1. 创建用户
    2. 登录
    3. 上传需求
    4. AI 生成场景
    5. 审核场景
    6. AI 生成用例
    7. 审核用例
    8. 创建环境
    9. 触发执行
    10. 查看报告
    """
    # 1. 创建用户
    user_response = client.post(
        "/api/v1/users",
        json={
            "username": "testuser",
            "password": "testpass",
            "email": "test@example.com",
            "role": "user"
        }
    )
    assert user_response.status_code == 201
    
    # 2. 登录
    login_response = client.post(
        "/api/v1/users/login",
        json={
            "username": "testuser",
            "password": "testpass"
        }
    )
    assert login_response.status_code == 200
    login_response.json()["access_token"]
    
    # 3. 创建需求
    req_response = client.post(
        "/api/v1/requirements",
        json={
            "title": "用户登录功能测试",
            "content": "测试用户登录功能，包括正常登录、错误密码、账号不存在等场景",
            "version": "v1.0"
        }
    )
    assert req_response.status_code == 201
    requirement_id = req_response.json()["id"]
    
    # 4. AI 生成场景
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
    
    # 5. 审核场景（批准）
    approve_scenario_response = client.post(
        f"/api/v1/scenarios/{scenario_id}/approve",
        json={
            "reviewer": "testuser",
            "comment": "场景合理"
        }
    )
    assert approve_scenario_response.status_code == 200
    
    # 6. AI 生成用例
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
    
    # 7. 审核用例（批准）
    approve_testcase_response = client.post(
        f"/api/v1/testcases/{testcase_id}/approve",
        json={
            "reviewer": "testuser",
            "comment": "用例完整"
        }
    )
    assert approve_testcase_response.status_code == 200
    
    # 8. 创建环境
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
    
    # 9. 触发执行
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
    execution_id = execution["id"]
    
    # 10. 查看执行状态
    status_response = client.get(f"/api/v1/executions/{execution_id}/status")
    assert status_response.status_code == 200
    
    # 11. 查看执行列表
    list_response = client.get("/api/v1/executions")
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1
    
    print("✅ 完整端到端测试通过！")


@pytest.mark.skip(reason="需要真实 AI 服务配置，暂时跳过")
def test_ai_config_workflow():
    """测试 AI 配置工作流"""
    # 创建 AI 配置
    config_response = client.post(
        "/api/v1/ai-configs",
        json={
            "name": "DeepSeek 需求分析",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "test_key",
            "base_url": "https://api.deepseek.com/v1",
            "assigned_steps": ["requirement_analysis"],
            "is_default": True
        }
    )
    assert config_response.status_code == 201
    config_id = config_response.json()["id"]
    
    # 查询配置
    get_response = client.get(f"/api/v1/ai-configs/{config_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "DeepSeek 需求分析"
    
    print("✅ AI 配置工作流测试通过！")
