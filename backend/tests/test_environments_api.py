"""
环境管理 API 单元测试

使用 conftest.py 中统一的测试数据库配置
"""
from fastapi.testclient import TestClient

from qualityfoundry.main import app

# 使用 conftest.py 中的 client fixture
client = TestClient(app)


def test_create_environment():
    """测试创建环境"""
    response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000",
            "variables": {"API_KEY": "test_key"},
            "credentials": "test_password"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "dev"
    assert data["base_url"] == "http://localhost:3000"
    # 凭证应该被加密
    assert data["credentials"] != "test_password"


def test_create_duplicate_environment():
    """测试创建重复环境名称"""
    # 创建第一个环境
    client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    
    # 尝试创建同名环境
    response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:4000"
        }
    )
    assert response.status_code == 400


def test_list_environments():
    """测试环境列表"""
    # 创建多个环境
    for name in ["dev", "sit", "uat"]:
        client.post(
            "/api/v1/environments",
            json={
                "name": name,
                "base_url": f"http://{name}.example.com"
            }
        )
    
    # 获取列表
    response = client.get("/api/v1/environments")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


def test_get_environment():
    """测试获取环境详情"""
    # 创建环境
    create_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    environment_id = create_response.json()["id"]
    
    # 获取详情
    response = client.get(f"/api/v1/environments/{environment_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == environment_id


def test_update_environment():
    """测试更新环境"""
    # 创建环境
    create_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    environment_id = create_response.json()["id"]
    
    # 更新环境
    response = client.put(
        f"/api/v1/environments/{environment_id}",
        json={
            "base_url": "http://localhost:4000",
            "is_active": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["base_url"] == "http://localhost:4000"
    assert data["is_active"] is False


def test_delete_environment():
    """测试删除环境"""
    # 创建环境
    create_response = client.post(
        "/api/v1/environments",
        json={
            "name": "dev",
            "base_url": "http://localhost:3000"
        }
    )
    environment_id = create_response.json()["id"]
    
    # 删除环境
    response = client.delete(f"/api/v1/environments/{environment_id}")
    assert response.status_code == 204
    
    # 验证已删除
    get_response = client.get(f"/api/v1/environments/{environment_id}")
    assert get_response.status_code == 404


def test_filter_active_environments():
    """测试筛选激活的环境"""
    # 创建环境
    env1 = client.post(
        "/api/v1/environments",
        json={"name": "dev", "base_url": "http://dev.example.com"}
    ).json()
    
    client.post(
        "/api/v1/environments",
        json={"name": "sit", "base_url": "http://sit.example.com"}
    )
    
    # 停用第一个环境
    client.put(
        f"/api/v1/environments/{env1['id']}",
        json={"is_active": False}
    )
    
    # 筛选激活的环境
    response = client.get("/api/v1/environments?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
