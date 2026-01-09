"""
安全防护测试
"""
import os
import pytest
from fastapi.testclient import TestClient

from qualityfoundry.main import app
from qualityfoundry.middleware.security import SecurityMiddleware

# 检测是否在 CI 环境中运行
IN_CI = os.environ.get("CI", "").lower() == "true" or os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

client = TestClient(app)


def test_sql_injection_detection():
    """测试 SQL 注入检测"""
    # 测试危险的 SQL 输入
    dangerous_inputs = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'--",
        "1 UNION SELECT * FROM users",
    ]
    
    for dangerous_input in dangerous_inputs:
        with pytest.raises(Exception):
            SecurityMiddleware.sanitize_sql_input(dangerous_input)


def test_xss_detection():
    """测试 XSS 检测"""
    # 测试危险的 XSS 输入
    dangerous_inputs = [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "<iframe src='malicious.com'></iframe>",
    ]
    
    for dangerous_input in dangerous_inputs:
        with pytest.raises(Exception):
            SecurityMiddleware.sanitize_xss_input(dangerous_input)


def test_safe_input():
    """测试安全输入"""
    safe_inputs = [
        "正常的用户输入",
        "user@example.com",
        "这是一个测试",
        "123456",
    ]
    
    for safe_input in safe_inputs:
        # 应该不抛出异常
        result = SecurityMiddleware.sanitize_sql_input(safe_input)
        assert result == safe_input


@pytest.mark.skipif(IN_CI, reason="安全头测试需要完整服务环境，在 CI 中跳过")
def test_security_headers():
    """测试安全响应头"""
    response = client.get("/api/v1/requirements")
    
    # 检查安全响应头
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "X-XSS-Protection" in response.headers
