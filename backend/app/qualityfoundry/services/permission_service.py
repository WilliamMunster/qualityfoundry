"""QualityFoundry - Permission Service

权限控制服务 - 管理用户角色和审核权限
"""
from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException, status

from qualityfoundry.database.user_models import User, UserRole


class Permission(str, Enum):
    """权限枚举"""
    # 需求权限
    REQUIREMENT_CREATE = "requirement:create"
    REQUIREMENT_READ = "requirement:read"
    REQUIREMENT_UPDATE = "requirement:update"
    REQUIREMENT_DELETE = "requirement:delete"
    
    # 场景权限
    SCENARIO_CREATE = "scenario:create"
    SCENARIO_READ = "scenario:read"
    SCENARIO_UPDATE = "scenario:update"
    SCENARIO_DELETE = "scenario:delete"
    
    # 用例权限
    TESTCASE_CREATE = "testcase:create"
    TESTCASE_READ = "testcase:read"
    TESTCASE_UPDATE = "testcase:update"
    TESTCASE_DELETE = "testcase:delete"
    
    # 审核权限
    APPROVAL_READ = "approval:read"
    APPROVAL_APPROVE = "approval:approve"
    APPROVAL_REJECT = "approval:reject"
    
    # 管理权限
    USER_MANAGE = "user:manage"
    CONFIG_MANAGE = "config:manage"
    SYSTEM_ADMIN = "system:admin"


# 角色权限映射
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.VIEWER: {
        Permission.REQUIREMENT_READ,
        Permission.SCENARIO_READ,
        Permission.TESTCASE_READ,
        Permission.APPROVAL_READ,
    },
    UserRole.USER: {
        # 继承 VIEWER 所有权限
        Permission.REQUIREMENT_READ,
        Permission.SCENARIO_READ,
        Permission.TESTCASE_READ,
        Permission.APPROVAL_READ,
        # 增加创建和更新权限
        Permission.REQUIREMENT_CREATE,
        Permission.REQUIREMENT_UPDATE,
        Permission.SCENARIO_CREATE,
        Permission.SCENARIO_UPDATE,
        Permission.TESTCASE_CREATE,
        Permission.TESTCASE_UPDATE,
    },
    UserRole.ADMIN: {
        # 所有权限
        Permission.REQUIREMENT_CREATE,
        Permission.REQUIREMENT_READ,
        Permission.REQUIREMENT_UPDATE,
        Permission.REQUIREMENT_DELETE,
        Permission.SCENARIO_CREATE,
        Permission.SCENARIO_READ,
        Permission.SCENARIO_UPDATE,
        Permission.SCENARIO_DELETE,
        Permission.TESTCASE_CREATE,
        Permission.TESTCASE_READ,
        Permission.TESTCASE_UPDATE,
        Permission.TESTCASE_DELETE,
        Permission.APPROVAL_READ,
        Permission.APPROVAL_APPROVE,
        Permission.APPROVAL_REJECT,
        Permission.USER_MANAGE,
        Permission.CONFIG_MANAGE,
        Permission.SYSTEM_ADMIN,
    },
}


class PermissionService:
    """权限服务"""
    
    @staticmethod
    def has_permission(user: User, permission: Permission) -> bool:
        """
        检查用户是否拥有指定权限
        
        Args:
            user: 用户对象
            permission: 权限
            
        Returns:
            是否有权限
        """
        if not user.is_active:
            return False
        
        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        return permission in user_permissions
    
    @staticmethod
    def has_any_permission(user: User, permissions: list[Permission]) -> bool:
        """检查用户是否拥有任一权限"""
        return any(PermissionService.has_permission(user, p) for p in permissions)
    
    @staticmethod
    def has_all_permissions(user: User, permissions: list[Permission]) -> bool:
        """检查用户是否拥有所有权限"""
        return all(PermissionService.has_permission(user, p) for p in permissions)
    
    @staticmethod
    def can_approve(user: User) -> bool:
        """检查用户是否可以进行审核"""
        return PermissionService.has_any_permission(
            user,
            [Permission.APPROVAL_APPROVE, Permission.SYSTEM_ADMIN]
        )
    
    @staticmethod
    def can_reject(user: User) -> bool:
        """检查用户是否可以拒绝审核"""
        return PermissionService.has_any_permission(
            user,
            [Permission.APPROVAL_REJECT, Permission.SYSTEM_ADMIN]
        )
    
    @staticmethod
    def get_user_permissions(user: User) -> set[Permission]:
        """获取用户所有权限"""
        if not user.is_active:
            return set()
        return ROLE_PERMISSIONS.get(user.role, set()).copy()


def require_permission(*permissions: Permission):
    """
    权限检查装饰器
    
    用法：
        @require_permission(Permission.APPROVAL_APPROVE)
        async def approve_endpoint(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取当前用户
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证"
                )
            
            # 检查权限
            if not PermissionService.has_any_permission(current_user, list(permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要以下权限之一: {[p.value for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """权限检查依赖"""
    
    def __init__(self, *permissions: Permission, require_all: bool = False):
        self.permissions = permissions
        self.require_all = require_all
    
    def __call__(self, current_user: Optional[User] = None) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未认证"
            )
        
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
                detail="权限不足"
            )
        
        return current_user
