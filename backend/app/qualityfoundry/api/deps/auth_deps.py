"""QualityFoundry - 认证依赖

提供 get_current_user 和权限检查依赖
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.user_models import User
from qualityfoundry.services.auth_service import AuthService
from qualityfoundry.services.permission_service import Permission, PermissionService


async def get_current_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization header 解析当前用户（走真实 token 校验）
    
    Args:
        authorization: Authorization header (Bearer token)
        db: 数据库会话
        
    Returns:
        当前用户
        
    Raises:
        HTTPException: 401 如果认证失败
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 提取 token（处理多余空格）
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证 token
    user = AuthService.verify_token(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


class PermissionRequired:
    """权限检查依赖（内部依赖 get_current_user）
    
    用法：
        @router.get("/protected")
        def protected_endpoint(
            user: User = Depends(PermissionRequired(Permission.ORCHESTRATION_RUN))
        ):
            ...
    """
    
    def __init__(self, *permissions: Permission, require_all: bool = False):
        self.permissions = permissions
        self.require_all = require_all
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """检查权限并返回用户"""
        if self.require_all:
            has_permission = PermissionService.has_all_permissions(
                current_user, list(self.permissions)
            )
        else:
            has_permission = PermissionService.has_any_permission(
                current_user, list(self.permissions)
            )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要以下权限之一: {[p.value for p in self.permissions]}",
            )
        
        return current_user


# 预定义权限检查器（用于 Router dependencies 或 endpoint）
RequireOrchestrationRun = PermissionRequired(Permission.ORCHESTRATION_RUN)
RequireOrchestrationRead = PermissionRequired(Permission.ORCHESTRATION_READ)
RequireArtifactRead = PermissionRequired(Permission.ARTIFACT_READ)
RequireAuditRead = PermissionRequired(Permission.AUDIT_READ)
RequireUserManage = PermissionRequired(Permission.USER_MANAGE)
