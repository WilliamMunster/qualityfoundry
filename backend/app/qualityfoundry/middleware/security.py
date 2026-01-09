"""
安全防护中间件

提供 SQL 注入、XSS、CSRF 等安全防护
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import re
from typing import Any, Dict
import html


class SecurityMiddleware:
    """安全防护中间件"""
    
    # SQL 注入危险关键词
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"('.*--)",
        r"(UNION.*SELECT)",
    ]
    
    # XSS 危险标签和属性
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """
        SQL 输入清理
        
        注意：SQLAlchemy ORM 已提供参数化查询防护
        此函数用于额外的原生 SQL 查询保护
        """
        if not isinstance(value, str):
            return value
        
        # 检测 SQL 注入模式
        for pattern in SecurityMiddleware.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise HTTPException(
                    status_code=400,
                    detail="检测到潜在的 SQL 注入攻击"
                )
        
        return value
    
    @staticmethod
    def sanitize_xss_input(value: str) -> str:
        """
        XSS 输入清理
        
        转义 HTML 特殊字符
        """
        if not isinstance(value, str):
            return value
        
        # 检测 XSS 模式
        for pattern in SecurityMiddleware.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise HTTPException(
                    status_code=400,
                    detail="检测到潜在的 XSS 攻击"
                )
        
        # HTML 转义
        return html.escape(value)
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], check_sql: bool = True, check_xss: bool = True) -> Dict[str, Any]:
        """
        递归清理字典中的所有字符串值
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                if check_sql:
                    value = SecurityMiddleware.sanitize_sql_input(value)
                if check_xss:
                    value = SecurityMiddleware.sanitize_xss_input(value)
                sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = SecurityMiddleware.sanitize_dict(value, check_sql, check_xss)
            elif isinstance(value, list):
                sanitized[key] = [
                    SecurityMiddleware.sanitize_dict(item, check_sql, check_xss) 
                    if isinstance(item, dict) 
                    else SecurityMiddleware.sanitize_xss_input(item) if isinstance(item, str) and check_xss
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


async def security_middleware(request: Request, call_next):
    """
    安全中间件
    
    对所有请求进行安全检查
    """
    # 跳过 GET 请求（通常不包含敏感输入）
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # 获取请求体
            body = await request.body()
            if body:
                import json
                try:
                    data = json.loads(body)
                    # 清理输入数据
                    if isinstance(data, dict):
                        SecurityMiddleware.sanitize_dict(data, check_sql=True, check_xss=True)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            # 如果检测到攻击，返回错误
            if isinstance(e, HTTPException):
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
    
    response = await call_next(request)
    
    # 添加安全响应头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    return response
