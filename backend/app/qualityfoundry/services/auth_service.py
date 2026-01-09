"""QualityFoundry - Auth Service

认证服务
"""
import hashlib
import secrets
from typing import Optional

from sqlalchemy.orm import Session

from qualityfoundry.database.user_models import User, UserRole


class AuthService:
    """认证服务"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return AuthService.hash_password(plain_password) == hashed_password
    
    @staticmethod
    def create_access_token(user_id: str) -> str:
        """创建访问令牌"""
        # 简化版本：实际应使用 JWT
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """认证用户"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user
    
    @staticmethod
    def create_default_admin(db: Session):
        """创建默认管理员"""
        # 检查是否已存在 admin 用户
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            return existing_admin
        
        # 创建默认管理员
        admin = User(
            username="admin",
            password_hash=AuthService.hash_password("admin"),
            email="admin@qualityfoundry.com",
            full_name="系统管理员",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
