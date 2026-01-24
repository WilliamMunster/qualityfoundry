"""Token 生命周期测试

测试登出、过期 token 和清理功能。
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from qualityfoundry.database.config import get_db
from qualityfoundry.database.token_models import UserToken
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.services.auth_service import AuthService


class TestLogout:
    """登出测试"""

    def test_logout_revokes_token(self, client):
        """登出后 token 立即失效"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # 使用测试数据库
        engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # 创建测试用户
            user = User(
                id=uuid4(),
                username=f"logout_test_{uuid4().hex[:8]}",
                password_hash=AuthService.hash_password("test123"),
                email="logout@test.com",
                full_name="Logout Test",
                role=UserRole.USER,
                is_active=True,
            )
            db.add(user)
            db.commit()
            
            # 创建 token
            token = AuthService.create_access_token(db, user.id)
            
            # 验证 token 有效
            verified_user = AuthService.verify_token(db, token)
            assert verified_user is not None
            assert verified_user.id == user.id
            
            # 撤销 token
            revoked = AuthService.revoke_token(db, token)
            assert revoked is True
            
            # 验证 token 失效
            verified_after_revoke = AuthService.verify_token(db, token)
            assert verified_after_revoke is None
            
        finally:
            db.close()

    def test_expired_token_rejected(self, client):
        """过期 token 被拒绝"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # 创建测试用户
            user = User(
                id=uuid4(),
                username=f"expired_test_{uuid4().hex[:8]}",
                password_hash=AuthService.hash_password("test123"),
                email="expired@test.com",
                full_name="Expired Test",
                role=UserRole.USER,
                is_active=True,
            )
            db.add(user)
            db.commit()
            
            # 手动创建过期 token
            expired_token_hash = AuthService._hash_token("expired_token_123")
            expired_token = UserToken(
                token_hash=expired_token_hash,
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # 已过期
            )
            db.add(expired_token)
            db.commit()
            
            # 验证过期 token 被拒绝
            verified = AuthService.verify_token(db, "expired_token_123")
            assert verified is None
            
        finally:
            db.close()


class TestTokenCleanup:
    """Token 清理测试"""

    def test_cleanup_does_not_affect_valid_tokens(self, client):
        """清理不影响有效 token"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # 创建测试用户
            user = User(
                id=uuid4(),
                username=f"cleanup_test_{uuid4().hex[:8]}",
                password_hash=AuthService.hash_password("test123"),
                email="cleanup@test.com",
                full_name="Cleanup Test",
                role=UserRole.USER,
                is_active=True,
            )
            db.add(user)
            db.commit()
            
            # 创建有效 token
            valid_token = AuthService.create_access_token(db, user.id)
            
            # 创建过期 token（用于被清理）
            expired_token_hash = AuthService._hash_token("to_be_cleaned")
            expired_token = UserToken(
                token_hash=expired_token_hash,
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            db.add(expired_token)
            db.commit()
            
            # 执行清理
            deleted_count = AuthService.cleanup_expired_tokens(db)
            assert deleted_count >= 1  # 至少清理了一个过期 token
            
            # 验证有效 token 仍然可用
            verified = AuthService.verify_token(db, valid_token)
            assert verified is not None
            assert verified.id == user.id
            
        finally:
            db.close()
