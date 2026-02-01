"""QualityFoundry - Tenant Context

多租户上下文管理
- 提供当前租户信息的上下文变量
- FastAPI 依赖注入支持
"""
from contextvars import ContextVar
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException, status

# 租户上下文变量（线程/协程安全）
tenant_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("tenant_ctx", default=None)


class TenantContext:
    """租户上下文管理器
    
    用于在请求生命周期内存储和访问当前租户信息。
    """
    
    @staticmethod
    def get_current() -> Optional[Dict[str, Any]]:
        """获取当前租户上下文
        
        Returns:
            包含 tenant_id, tenant_role 等信息的字典，如果没有则返回 None
        """
        return tenant_ctx.get()
    
    @staticmethod
    def get_tenant_id() -> Optional[str]:
        """获取当前租户ID"""
        ctx = tenant_ctx.get()
        if ctx:
            return ctx.get("tenant_id")
        return None
    
    @staticmethod
    def get_tenant_role() -> Optional[str]:
        """获取当前租户角色"""
        ctx = tenant_ctx.get()
        if ctx:
            return ctx.get("tenant_role", "member")
        return None
    
    @staticmethod
    def set(tenant_id: str, tenant_role: str = "member", **extra) -> None:
        """设置当前租户上下文
        
        Args:
            tenant_id: 租户ID
            tenant_role: 租户内角色
            **extra: 其他租户相关信息
        """
        tenant_ctx.set({
            "tenant_id": tenant_id,
            "tenant_role": tenant_role,
            **extra
        })
    
    @staticmethod
    def clear() -> None:
        """清除当前租户上下文"""
        tenant_ctx.set(None)


async def get_tenant_context(
    request: Request,
) -> Optional[Dict[str, Any]]:
    """FastAPI 依赖：获取当前租户上下文
    
    从请求中解析 JWT 令牌，提取租户信息。
    非多租户端点可以返回 None。
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        租户上下文字典或 None
    """
    # 从 Authorization header 提取 token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return None
    
    # 从 token 提取租户信息
    from qualityfoundry.services.auth_service import AuthService
    tenant_info = AuthService.get_tenant_from_token(token)
    
    if tenant_info:
        # 设置上下文
        TenantContext.set(
            tenant_id=tenant_info["tenant_id"],
            tenant_role=tenant_info["tenant_role"]
        )
    
    return tenant_info


async def require_tenant(
    request: Request,
) -> Dict[str, Any]:
    """FastAPI 依赖：要求必须有多租户上下文
    
    与 get_tenant_context 类似，但如果无法获取租户信息会抛出 403 错误。
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        租户上下文字典
        
    Raises:
        HTTPException: 403 如果没有租户信息
    """
    tenant = await get_tenant_context(request)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此操作需要选择租户（工作空间）",
        )
    
    return tenant


class TenantMiddleware:
    """租户上下文中间件
    
    在每个请求开始时设置租户上下文，请求结束时清除。
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # 创建请求对象
        request = Request(scope, receive)
        
        # 尝试解析租户信息
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            if token:
                from qualityfoundry.services.auth_service import AuthService
                tenant_info = AuthService.get_tenant_from_token(token)
                if tenant_info:
                    TenantContext.set(
                        tenant_id=tenant_info["tenant_id"],
                        tenant_role=tenant_info["tenant_role"]
                    )
        
        try:
            await self.app(scope, receive, send)
        finally:
            # 请求结束时清除上下文
            TenantContext.clear()
