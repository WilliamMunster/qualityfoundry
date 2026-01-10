"""QualityFoundry - System Config Models

系统配置模型 - 存储通知、邮件、Webhook 等系统级配置
"""
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from qualityfoundry.database.config import Base


class ConfigCategory(str, Enum):
    """配置分类"""
    NOTIFICATION = "notification"  # 通知配置
    EMAIL = "email"                # 邮件配置
    WEBHOOK = "webhook"            # Webhook 配置
    SYSTEM = "system"              # 系统配置
    SECURITY = "security"          # 安全配置
    MCP = "mcp"                    # MCP 配置


class SystemConfig(Base):
    """系统配置模型"""
    __tablename__ = "system_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(50), nullable=False, index=True)  # 配置分类
    key = Column(String(100), nullable=False, index=True)      # 配置键
    value = Column(Text, nullable=True)                        # 配置值（字符串）
    value_json = Column(JSON, nullable=True)                   # 配置值（JSON）
    description = Column(String(500), nullable=True)           # 配置描述
    is_secret = Column(Boolean, default=False)                 # 是否敏感信息
    is_active = Column(Boolean, default=True)                  # 是否启用
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # 唯一约束：category + key
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    def get_value(self):
        """获取配置值"""
        if self.value_json is not None:
            return self.value_json
        return self.value
    
    def set_value(self, value):
        """设置配置值"""
        if isinstance(value, (dict, list)):
            self.value_json = value
            self.value = None
        else:
            self.value = str(value) if value is not None else None
            self.value_json = None


# 预定义配置键
class ConfigKey:
    """预定义配置键"""
    # 邮件配置
    EMAIL_ENABLED = "email_enabled"
    EMAIL_SMTP_HOST = "email_smtp_host"
    EMAIL_SMTP_PORT = "email_smtp_port"
    EMAIL_SMTP_USER = "email_smtp_user"
    EMAIL_SMTP_PASSWORD = "email_smtp_password"
    EMAIL_SMTP_TLS = "email_smtp_tls"
    EMAIL_FROM = "email_from"
    EMAIL_FROM_NAME = "email_from_name"
    
    # Webhook 配置
    WEBHOOK_ENABLED = "webhook_enabled"
    WEBHOOK_URL = "webhook_url"
    WEBHOOK_SECRET = "webhook_secret"
    WEBHOOK_TIMEOUT = "webhook_timeout"
    
    # 通知配置
    NOTIFICATION_ON_APPROVAL = "notification_on_approval"
    NOTIFICATION_ON_REJECTION = "notification_on_rejection"
    NOTIFICATION_RECIPIENTS = "notification_recipients"
    
    # 系统配置
    SYSTEM_NAME = "system_name"
    SYSTEM_LOGO_URL = "system_logo_url"
    SYSTEM_MAINTENANCE_MODE = "system_maintenance_mode"
    
    # MCP 配置
    MCP_ENABLED = "mcp_enabled"
    MCP_SERVER_COMMAND = "mcp_server_command"
    MCP_SERVER_ARGS = "mcp_server_args"
    MCP_SERVER_URL = "mcp_server_url"
    MCP_MAX_RETRIES = "mcp_max_retries"
    MCP_TIMEOUT = "mcp_timeout"
