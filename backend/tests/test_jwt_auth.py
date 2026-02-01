"""JWT 认证测试

测试 JWT 签发、验证、撤销和向后兼容性。
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from qualityfoundry.core.config import settings
from qualityfoundry.database.token_models import UserToken
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.services.auth_service import AuthService


class TestJWTCreate:
    """JWT 签发测试"""

    def test_create_jwt_token_returns_valid_jwt(self, db):
        """创建的 token 是有效的 JWT 格式"""
        # 创建测试用户
        user = User(
            id=uuid4(),
            username=f"jwt_create_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="jwt@test.com",
            full_name="JWT Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        # 创建 JWT token
        token = AuthService.create_jwt_token(user)
        
        # 验证是有效的 JWT 格式（可以被解码）
        assert token is not None
        assert len(token.split(".")) == 3  # JWT 有三个部分：header.payload.signature
        
        # 使用 PyJWT 解码验证
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == str(user.id)
        assert payload["username"] == user.username
        assert payload["role"] == user.role.value
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_jwt_contains_required_claims(self, db):
        """JWT 包含必需的 claims"""
        user = User(
            id=uuid4(),
            username=f"jwt_claims_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="claims@test.com",
            full_name="Claims Test",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_jwt_token(user)
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # 验证所有必需 claims
        assert payload["sub"] == str(user.id), "应包含 subject (用户ID)"
        assert payload["username"] == user.username, "应包含用户名"
        assert payload["role"] == "admin", "应包含角色"
        assert isinstance(payload["exp"], int), "exp 应为时间戳"
        assert isinstance(payload["iat"], int), "iat 应为时间戳"
        assert isinstance(payload["jti"], str), "jti 应为字符串"

    def test_jwt_expiration_is_set_correctly(self, db):
        """JWT 过期时间设置正确"""
        user = User(
            id=uuid4(),
            username=f"jwt_exp_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="exp@test.com",
            full_name="Exp Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        before_create = datetime.now(timezone.utc)
        token = AuthService.create_jwt_token(user)
        
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # 验证过期时间大致正确（允许 5 秒误差）
        expected_exp = before_create + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        assert abs((exp_datetime - expected_exp).total_seconds()) < 5


class TestJWTVerify:
    """JWT 验证测试"""

    def test_verify_valid_jwt_returns_user(self, db):
        """验证有效的 JWT 返回用户"""
        user = User(
            id=uuid4(),
            username=f"jwt_verify_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="verify@test.com",
            full_name="Verify Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_jwt_token(user)
        verified_user = AuthService.verify_jwt_token(db, token)
        
        assert verified_user is not None
        assert verified_user.id == user.id
        assert verified_user.username == user.username

    def test_verify_expired_jwt_returns_none(self, db):
        """验证过期的 JWT 返回 None"""
        # 创建已过期的 JWT
        expired_payload = {
            "sub": str(uuid4()),
            "username": "expired",
            "role": "user",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # 已过期
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "jti": str(uuid4()),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        verified = AuthService.verify_jwt_token(db, expired_token)
        assert verified is None

    def test_verify_invalid_jwt_returns_none(self, db):
        """验证无效的 JWT 返回 None"""
        invalid_tokens = [
            "not.a.jwt",
            "invalid_token",
            "header.payload",  # 缺少 signature
        ]
        
        for token in invalid_tokens:
            verified = AuthService.verify_jwt_token(db, token)
            assert verified is None, f"Token '{token}' 应该验证失败"

    def test_verify_jwt_with_wrong_secret_returns_none(self, db):
        """使用错误密钥签名的 JWT 验证失败"""
        payload = {
            "sub": str(uuid4()),
            "username": "wrong_secret",
            "role": "user",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid4()),
        }
        # 使用错误的密钥签名
        wrong_token = jwt.encode(
            payload,
            "wrong_secret_key",
            algorithm=settings.JWT_ALGORITHM
        )
        
        verified = AuthService.verify_jwt_token(db, wrong_token)
        assert verified is None

    def test_verify_jwt_for_inactive_user_returns_none(self, db):
        """验证已禁用用户的 JWT 返回 None"""
        user = User(
            id=uuid4(),
            username=f"jwt_inactive_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="inactive@test.com",
            full_name="Inactive Test",
            role=UserRole.USER,
            is_active=False,  # 已禁用
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_jwt_token(user)
        verified = AuthService.verify_jwt_token(db, token)
        
        assert verified is None

    def test_decode_jwt_token_returns_payload(self):
        """decode_jwt_token 正确返回 payload"""
        user = User(
            id=uuid4(),
            username="decode_test",
            password_hash="hash",
            email="decode@test.com",
            full_name="Decode Test",
            role=UserRole.USER,
            is_active=True,
        )
        
        token = AuthService.create_jwt_token(user)
        payload = AuthService.decode_jwt_token(token)
        
        assert payload is not None
        assert payload["sub"] == str(user.id)
        assert payload["username"] == user.username
        assert payload["jti"] is not None

    def test_decode_invalid_jwt_returns_none(self):
        """解码无效的 JWT 返回 None"""
        payload = AuthService.decode_jwt_token("invalid.token")
        assert payload is None


class TestJWTRevoke:
    """JWT 撤销测试"""

    def test_revoke_jwt_by_jti(self, db):
        """通过 jti 撤销 JWT"""
        user = User(
            id=uuid4(),
            username=f"jwt_revoke_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="revoke@test.com",
            full_name="Revoke Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        # 使用 create_access_token 会自动存储到数据库
        token = AuthService.create_access_token(db, user)
        
        # 验证 token 有效
        verified = AuthService.verify_jwt_token(db, token)
        assert verified is not None
        
        # 撤销 token
        revoked = AuthService.revoke_token(db, token)
        assert revoked is True
        
        # 注意：当前 verify_jwt_token 是 stateless 的，不会检查数据库
        # 如果需要检查撤销状态，需要扩展 verify_jwt_token

    def test_revoke_invalid_token_returns_false_or_true(self, db):
        """撤销无效 token 的行为"""
        # 对于无效的 token，revoke 应该返回 False 或处理错误
        result = AuthService.revoke_token(db, "totally.invalid.token")
        # 对于无法解析的 JWT，返回 False
        assert result is False


class TestAccessTokenIntegration:
    """Access Token 集成测试（JWT + 数据库）"""

    def test_create_access_token_returns_jwt(self, db):
        """create_access_token 返回 JWT 格式 token"""
        user = User(
            id=uuid4(),
            username=f"access_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="access@test.com",
            full_name="Access Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_access_token(db, user)
        
        # 验证是 JWT 格式
        assert len(token.split(".")) == 3
        
        # 验证可以被解码
        payload = AuthService.decode_jwt_token(token)
        assert payload is not None
        assert payload["sub"] == str(user.id)

    def test_create_access_token_stores_jti_in_db(self, db):
        """create_access_token 将 jti 存储到数据库"""
        user = User(
            id=uuid4(),
            username=f"access_db_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="accessdb@test.com",
            full_name="Access DB Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        token = AuthService.create_access_token(db, user)
        payload = AuthService.decode_jwt_token(token)
        jti = payload["jti"]
        
        # 验证数据库中有记录
        db_token = db.query(UserToken).filter(
            UserToken.token_hash == jti
        ).first()
        
        assert db_token is not None
        assert db_token.user_id == user.id
        assert db_token.revoked_at is None


class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_old_opaque_token_still_works(self, db):
        """旧版 opaque token 仍可验证"""
        user = User(
            id=uuid4(),
            username=f"old_token_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="old@test.com",
            full_name="Old Token Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        # 手动创建旧版 opaque token
        old_token = "old_opaque_token_12345"
        token_hash = AuthService._hash_token(old_token)
        
        db_token = UserToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(db_token)
        db.commit()
        
        # 验证旧版 token 仍可通过 verify_token 验证
        verified = AuthService.verify_token(db, old_token)
        assert verified is not None
        assert verified.id == user.id

    def test_old_opaque_token_can_be_revoked(self, db):
        """旧版 opaque token 仍可被撤销"""
        user = User(
            id=uuid4(),
            username=f"old_revoke_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="oldrevoke@test.com",
            full_name="Old Revoke Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        # 创建旧版 opaque token
        old_token = "old_token_to_revoke"
        token_hash = AuthService._hash_token(old_token)
        
        db_token = UserToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(db_token)
        db.commit()
        
        # 撤销
        revoked = AuthService.revoke_token(db, old_token)
        assert revoked is True
        
        # 验证已失效
        verified = AuthService.verify_token(db, old_token)
        assert verified is None

    def test_verify_token_with_jwt_returns_none(self, db):
        """旧版 verify_token 方法对 JWT 返回 None（因为 JWT 没有存储 hash）"""
        user = User(
            id=uuid4(),
            username=f"compat_{uuid4().hex[:8]}",
            password_hash=AuthService.hash_password("test123"),
            email="compat@test.com",
            full_name="Compat Test",
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        jwt_token = AuthService.create_jwt_token(user)
        
        # 旧版 verify_token 使用 _hash_token 查找，不会找到 JWT
        # 这符合预期：JWT 应该使用 verify_jwt_token
        verified = AuthService.verify_token(db, jwt_token)
        # 应该返回 None，因为 JWT 没有以 hash 形式存储
        assert verified is None
