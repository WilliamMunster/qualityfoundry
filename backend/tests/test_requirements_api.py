"""
需求管理 API 单元测试

使用 conftest.py 中统一的测试数据库配置
"""
from fastapi.testclient import TestClient

from qualityfoundry.main import app

# 使用 conftest.py 中的 client fixture
client = TestClient(app)


def test_create_requirement():
    """测试创建需求"""
    response = client.post(
        "/api/v1/requirements",
        json={
            "title": "测试需求",
            "content": "这是测试内容",
            "version": "v1.0"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "测试需求"
    assert data["content"] == "这是测试内容"
    assert data["version"] == "v1.0"
    assert "id" in data


def test_list_requirements():
    """测试需求列表"""
    # 创建几个需求
    for i in range(3):
        client.post(
            "/api/v1/requirements",
            json={
                "title": f"需求{i}",
                "content": f"内容{i}",
                "version": "v1.0"
            }
        )
    
    # 获取列表
    response = client.get("/api/v1/requirements")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_get_requirement():
    """测试获取需求详情"""
    # 创建需求
    create_response = client.post(
        "/api/v1/requirements",
        json={
            "title": "测试需求",
            "content": "测试内容",
            "version": "v1.0"
        }
    )
    requirement_id = create_response.json()["id"]
    
    # 获取详情
    response = client.get(f"/api/v1/requirements/{requirement_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == requirement_id
    assert data["title"] == "测试需求"


def test_update_requirement():
    """测试更新需求"""
    # 创建需求
    create_response = client.post(
        "/api/v1/requirements",
        json={
            "title": "原标题",
            "content": "原内容",
            "version": "v1.0"
        }
    )
    requirement_id = create_response.json()["id"]
    
    # 更新需求
    response = client.put(
        f"/api/v1/requirements/{requirement_id}",
        json={
            "title": "新标题",
            "content": "新内容"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "新标题"
    assert data["content"] == "新内容"


def test_delete_requirement():
    """测试删除需求"""
    # 创建需求
    create_response = client.post(
        "/api/v1/requirements",
        json={
            "title": "待删除需求",
            "content": "待删除内容",
            "version": "v1.0"
        }
    )
    requirement_id = create_response.json()["id"]
    
    # 删除需求
    response = client.delete(f"/api/v1/requirements/{requirement_id}")
    assert response.status_code == 204
    
    # 验证已删除
    get_response = client.get(f"/api/v1/requirements/{requirement_id}")
    assert get_response.status_code == 404


def test_search_requirements():
    """测试需求搜索"""
    # 创建需求
    client.post(
        "/api/v1/requirements",
        json={
            "title": "登录功能需求",
            "content": "用户登录相关需求",
            "version": "v1.0"
        }
    )
    client.post(
        "/api/v1/requirements",
        json={
            "title": "注册功能需求",
            "content": "用户注册相关需求",
            "version": "v1.0"
        }
    )
    
    # 搜索"登录"
    response = client.get("/api/v1/requirements?search=登录")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert "登录" in data["items"][0]["title"]
