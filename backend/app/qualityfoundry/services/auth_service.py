"""QualityFoundry - Auth Service

认证服务
"""
import hashlib
import uuid as uuid_module
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import InvalidTokenError

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
    
    # ========== JWT 相关方法 ==========
    
    @staticmethod
    def create_jwt_token(
        user: User,
        tenant_id: Optional[str] = None,
        tenant_role: Optional[str] = None
    ) -> str:
        """创建 JWT 令牌
        
        Args:
            user: 用户对象
            tenant_id: 可选的租户ID（多租户场景）
            tenant_role: 可选的租户内角色（多租户场景）
            
        Returns:
            JWT 令牌字符串
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        jti = str(uuid_module.uuid4())  # 用于撤销追踪的唯一ID
        
        payload: Dict[str, Any] = {
            "sub": str(user.id),           # 主题：用户ID
            "username": user.username,      # 用户名
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "exp": expires_at,              # 过期时间
            "iat": now,                     # 签发时间
            "jti": jti,                     # 令牌唯一ID
        }
        
        # 多租户字段（可选）
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if tenant_role:
            payload["tenant_role"] = tenant_role
        
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return token
    
    @staticmethod
    def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
        """解码并验证 JWT 令牌
        
        Args:
            token: JWT 令牌字符串
            
        Returns:
            解码后的 payload 字典，验证失败返回 None
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except InvalidTokenError:
            return None
    
    @staticmethod
    def get_tenant_from_token(token: str) -> Optional[Dict[str, str]]:
        """从 JWT 令牌中提取租户信息
        
        Args:
            token: JWT 令牌字符串
            
        Returns:
            包含 tenant_id 和 tenant_role 的字典，如果没有则返回 None
        """
        payload = AuthService.decode_jwt_token(token)
        if not payload:
            return None
        
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            return None
        
        return {
            "tenant_id": tenant_id,
            "tenant_role": payload.get("tenant_role", "member"),
        }
    
    @staticmethod
    def verify_jwt_token(db: Session, token: str) -> Optional[User]:
        """验证 JWT 令牌并返回用户
        
        支持 stateless 验证，如需检查撤销状态可扩展。
        
        Args:
            db: 数据库会话
            token: JWT 令牌字符串
            
        Returns:
            有效则返回 User，无效返回 None
        """
        payload = AuthService.decode_jwt_token(token)
        if not payload:
            return None
        
        # 获取用户ID
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            return None
        
        # 查询用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None
        
        return user
    
    @staticmethod
    def create_access_token(db: Session, user: User) -> str:
        """创建访问令牌（JWT 格式）
        
        创建 JWT 令牌并可选存储到数据库用于撤销追踪。
        
        Args:
            db: 数据库会话
            user: 用户对象
            
        Returns:
            JWT 令牌字符串
        """
        # 创建 JWT 令牌
        token = AuthService.create_jwt_token(user)
        
        # 解析 jti 用于数据库记录（支持撤销）
        payload = AuthService.decode_jwt_token(token)
        if payload:
            jti = payload.get("jti")
            expires_at = payload.get("exp")
            if expires_at:
                expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
            
            # 使用 jti 作为 token_hash 存储（用于撤销追踪）
            db_token = UserToken(
                token_hash=jti,  # 存储 jti 用于撤销追踪
                user_id=user.id,
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
        
        支持撤销 JWT（通过 jti）和旧版 opaque token。
        
        Args:
            db: 数据库会话
            token: 原始 token（JWT 或旧版 opaque token）
            
        Returns:
            是否成功撤销
        """
        # 首先尝试作为 JWT 解析
        payload = AuthService.decode_jwt_token(token)
        if payload:
            # JWT 模式：使用 jti 作为查找键
            jti = payload.get("jti")
            if not jti:
                return False
            
            db_token = db.query(UserToken).filter(
                UserToken.token_hash == jti,
                UserToken.revoked_at.is_(None),
            ).first()
            
            if not db_token:
                # Token 可能已过期被清理，但视为撤销成功
                return True
            
            db_token.revoked_at = datetime.now(timezone.utc)
            db.commit()
            return True
        
        # 回退：旧版 opaque token 模式
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

