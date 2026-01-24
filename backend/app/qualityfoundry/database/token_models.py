"""QualityFoundry - Token Models

用户访问令牌存储模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from qualityfoundry.database.config import Base


class UserToken(Base):
    """用户访问令牌模型
    
    存储用户登录生成的 token，支持验证、过期和撤销。
    """
    __tablename__ = "user_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256 hash
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # 关联
    user = relationship("User", backref="tokens")

    # 复合索引：用于快速验证有效 token
    __table_args__ = (
        Index("ix_user_tokens_hash_expires", "token_hash", "expires_at"),
    )
