"""Test AI Review Routes

AI 评审 API 路由测试
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from qualityfoundry.api.v1.routes_ai_review import router
from qualityfoundry.governance.tracing.collector import (
    TraceCollector,
)


# 创建测试客户端
@pytest.fixture
def client():
    """测试客户端"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestAIReviewConfigEndpoint:
    """测试 AI 评审配置端点"""

    def test_get_ai_review_config(self, client):
        """获取 AI 评审配置"""
        response = client.get("/ai-review/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应结构
        assert "enabled" in data
        assert "strategy" in data
        assert "models_count" in data
        assert "models" in data
        assert "thresholds" in data
        assert "dimensions" in data

    def test_config_has_required_fields(self, client):
        """配置包含必需字段"""
        response = client.get("/ai-review/config")
        data = response.json()
        
        assert isinstance(data["enabled"], bool)
        assert isinstance(data["strategy"], str)
        assert isinstance(data["models_count"], int)
        assert isinstance(data["models"], list)
        assert "pass_confidence" in data["thresholds"]
        assert "hitl_confidence" in data["thresholds"]

    def test_models_do_not_have_sensitive_data(self, client):
        """模型配置不包含敏感数据"""
        response = client.get("/ai-review/config")
        data = response.json()
        
        for model in data["models"]:
            # 不应包含 API key
            assert "api_key" not in model
            # 应有基本字段
            assert "name" in model
            assert "provider" in model
            assert "weight" in model
            assert "temperature" in model


class TestRunAIReviewEndpoint:
    """测试 Run AI 评审结果端点"""

    def test_get_run_ai_review_not_found(self, client):
        """获取不存在的 Run 返回 404"""
        fake_uuid = uuid4()
        response = client.get(f"/ai-review/runs/{fake_uuid}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_run_ai_review_with_data(self, client):
        """获取有 AI 评审数据的 Run"""
        run_id = uuid4()
        
        # 创建 collector 并保存 evidence（使用默认 artifact_root）
        collector = TraceCollector(
            run_id=str(run_id),
            input_nl="Test",
        )
        
        # 设置 AI 评审结果
        ai_result = {
            "verdict": "PASS",
            "confidence": 0.92,
            "reasoning": "All checks passed",
            "model_votes": [
                {"model": "gpt-4", "verdict": "PASS", "confidence": 0.93},
            ],
            "metadata": {"review_id": str(uuid4())},
        }
        collector.set_ai_review_result(ai_result)
        
        # 保存 evidence
        evidence, _ = collector.collect_and_save()
        
        # 调用 API
        response = client.get(f"/ai-review/runs/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == str(run_id)
        assert data["has_ai_review"] is True
        assert data["ai_review"]["verdict"] == "PASS"
        assert data["ai_review"]["confidence"] == 0.92

    def test_get_run_without_ai_review(self, client):
        """获取无 AI 评审数据的 Run"""
        run_id = uuid4()
        
        # 创建无 AI 评审的 evidence（使用默认 artifact_root）
        collector = TraceCollector(
            run_id=str(run_id),
            input_nl="Test",
        )
        collector.collect_and_save()
        
        # 调用 API
        response = client.get(f"/ai-review/runs/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == str(run_id)
        assert data["has_ai_review"] is False
        assert data["ai_review"] is None


class TestAIReviewHealthEndpoint:
    """测试 AI 评审健康检查端点"""

    def test_health_check(self, client):
        """健康检查返回状态"""
        response = client.get("/ai-review/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "ai_review_enabled" in data
        assert "configured_models" in data
        assert "strategy" in data
        assert isinstance(data["ai_review_enabled"], bool)
        assert isinstance(data["configured_models"], int)


class TestAIReviewIntegration:
    """测试完整集成流程"""

    def test_end_to_end_config_and_result(self, client):
        """端到端：配置 → 执行 → 结果查询"""
        # 1. 获取配置
        config_response = client.get("/ai-review/config")
        assert config_response.status_code == 200
        config = config_response.json()
        
        # 2. 创建带 AI 评审的 evidence
        run_id = uuid4()
        collector = TraceCollector(
            run_id=str(run_id),
            input_nl="Test with AI review",
        )
        
        ai_result = {
            "verdict": "NEEDS_HITL",
            "confidence": 0.65,
            "hitl_triggered": True,
            "model_votes": [
                {"model": m["name"], "verdict": "NEEDS_HITL", "confidence": 0.65}
                for m in config["models"][:1]  # 使用配置中的模型
            ] if config["models"] else [],
            "metadata": {"review_id": str(uuid4())},
        }
        collector.set_ai_review_result(ai_result)
        collector.collect_and_save()
        
        # 3. 查询结果
        result_response = client.get(f"/ai-review/runs/{run_id}")
        assert result_response.status_code == 200
        
        result = result_response.json()
        assert result["has_ai_review"] is True
        assert result["ai_review"]["verdict"] == "NEEDS_HITL"
