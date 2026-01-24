"""QualityFoundry - Auth Service

认证服务
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from qualityfoundry.core.config import settings
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.database.token_models import UserToken


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
    def _hash_token(token: str) -> str:
        """Token 哈希（带 pepper 防止离线碰撞）"""
        salted = token + settings.TOKEN_PEPPER
        return hashlib.sha256(salted.encode()).hexdigest()
    
    @staticmethod
    def create_access_token(db: Session, user_id: UUID) -> str:
        """创建访问令牌并存储到数据库
        
        Args:
            db: 数据库会话
            user_id: 用户 ID
            
        Returns:
            原始 token（返回给客户端）
        """
        token = secrets.token_urlsafe(32)
        token_hash = AuthService._hash_token(token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.TOKEN_EXPIRE_HOURS)
        
        db_token = UserToken(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.add(db_token)
        db.commit()
        
        return token
    
    @staticmethod
    def verify_token(db: Session, token: str) -> Optional[User]:
        """验证 token 并返回用户
        
        Args:
            db: 数据库会话
            token: 原始 token
            
        Returns:
            有效则返回 User，无效返回 None
        """
        token_hash = AuthService._hash_token(token)
        
        db_token = db.query(UserToken).filter(
            UserToken.token_hash == token_hash,
            UserToken.expires_at > datetime.now(timezone.utc),
            UserToken.revoked_at.is_(None),
        ).first()
        
        if not db_token:
            return None
        
        user = db.query(User).filter(User.id == db_token.user_id).first()
        if not user or not user.is_active:
            return None
        
        return user
    
    @staticmethod
    def revoke_token(db: Session, token: str) -> bool:
        """撤销 token（用于登出）
        
        Args:
            db: 数据库会话
            token: 原始 token
            
        Returns:
            是否成功撤销
        """
        token_hash = AuthService._hash_token(token)
        
        db_token = db.query(UserToken).filter(
            UserToken.token_hash == token_hash,
            UserToken.revoked_at.is_(None),
        ).first()
        
        if not db_token:
            return False
        
        db_token.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True
    
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

    @staticmethod
    def cleanup_expired_tokens(db: Session, retention_days: int = 7) -> int:
        """清理过期和已撤销的 token
        
        清理规则：
        - 条件1：已过期的 token（expires_at < now）
        - 条件2：已撤销且超过保留期的 token（revoked_at IS NOT NULL AND revoked_at < cutoff）
        
        Args:
            db: 数据库会话
            retention_days: 已撤销 token 保留天数（默认 7 天）
            
        Returns:
            删除的 token 数量
        """
        from sqlalchemy import and_, or_
        
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=retention_days)
        
        deleted = db.query(UserToken).filter(
            or_(
                UserToken.expires_at < now,
                and_(
                    UserToken.revoked_at.isnot(None),
                    UserToken.revoked_at < cutoff
                )
            )
        ).delete(synchronize_session=False)
        
        db.commit()
        return deleted

