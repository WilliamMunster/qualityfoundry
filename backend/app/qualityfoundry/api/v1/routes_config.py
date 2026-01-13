"""QualityFoundry - Config API Routes

配置管理 API - 系统配置、通知配置、邮件配置等
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.system_config_models import SystemConfig, ConfigCategory, ConfigKey

router = APIRouter(prefix="/configs", tags=["configs"])


# ================== Schemas ==================

class ConfigBase(BaseModel):
    """配置基础 Schema"""
    category: str = Field(..., description="配置分类")
    key: str = Field(..., description="配置键")
    value: Optional[str] = Field(None, description="配置值（字符串）")
    value_json: Optional[dict | list] = Field(None, description="配置值（JSON）")
    description: Optional[str] = Field(None, description="配置描述")
    is_secret: bool = Field(False, description="是否敏感信息")
    is_active: bool = Field(True, description="是否启用")


class ConfigCreate(ConfigBase):
    """创建配置"""
    pass


class ConfigUpdate(BaseModel):
    """更新配置"""
    value: Optional[str] = None
    value_json: Optional[dict | list] = None
    description: Optional[str] = None
    is_secret: Optional[bool] = None
    is_active: Optional[bool] = None


class ConfigResponse(ConfigBase):
    """配置响应"""
    id: UUID
    created_at: str
    updated_at: str
    
    model_config = ConfigDict(from_attributes=True)


class ConfigGroupResponse(BaseModel):
    """配置组响应"""
    category: str
    configs: List[ConfigResponse]


class NotificationConfigUpdate(BaseModel):
    """通知配置更新"""
    email_enabled: bool = False
    email_smtp_host: Optional[str] = None
    email_smtp_port: int = 587
    email_smtp_user: Optional[str] = None
    email_smtp_password: Optional[str] = None
    email_smtp_tls: bool = True
    email_from: Optional[str] = None
    email_from_name: Optional[str] = None
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_timeout: int = 10


class NotificationConfigResponse(NotificationConfigUpdate):
    """通知配置响应"""
    pass


class MCPConfigUpdate(BaseModel):
    """MCP 配置更新"""
    mcp_enabled: bool = False
    mcp_server_command: str = "npx"
    mcp_server_args: str = "-y @modelcontextprotocol/server-playwright"
    mcp_server_url: Optional[str] = None
    mcp_max_retries: int = 3
    mcp_timeout: int = 30


class MCPConfigResponse(MCPConfigUpdate):
    """MCP 配置响应"""
    pass


# ================== Helper Functions ==================

def get_or_create_config(
    db: Session,
    category: str,
    key: str,
    default_value: Optional[str] = None,
    description: Optional[str] = None
) -> SystemConfig:
    """获取或创建配置"""
    config = db.query(SystemConfig).filter(
        SystemConfig.category == category,
        SystemConfig.key == key
    ).first()
    
    if not config:
        config = SystemConfig(
            category=category,
            key=key,
            value=default_value,
            description=description
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return config


def set_config_value(
    db: Session,
    category: str,
    key: str,
    value,
    description: Optional[str] = None,
    is_secret: bool = False
):
    """设置配置值"""
    config = get_or_create_config(db, category, key)
    config.set_value(value)
    if description:
        config.description = description
    config.is_secret = is_secret
    db.commit()
    db.refresh(config)
    return config


def get_config_value(db: Session, category: str, key: str, default=None):
    """获取配置值"""
    config = db.query(SystemConfig).filter(
        SystemConfig.category == category,
        SystemConfig.key == key,
        SystemConfig.is_active
    ).first()
    
    if config:
        return config.get_value()
    return default


# ================== API Endpoints ==================

@router.get("/", response_model=List[ConfigResponse])
def list_configs(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取配置列表"""
    query = db.query(SystemConfig)
    if category:
        query = query.filter(SystemConfig.category == category)
    
    configs = query.order_by(SystemConfig.category, SystemConfig.key).all()
    
    # 隐藏敏感信息
    result = []
    for config in configs:
        config_dict = {
            "id": config.id,
            "category": config.category,
            "key": config.key,
            "value": "******" if config.is_secret and config.value else config.value,
            "value_json": config.value_json,
            "description": config.description,
            "is_secret": config.is_secret,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
        result.append(config_dict)
    
    return result


@router.get("/categories", response_model=List[str])
def list_categories():
    """获取配置分类列表"""
    return [c.value for c in ConfigCategory]


@router.get("/notification", response_model=NotificationConfigResponse)
def get_notification_config(db: Session = Depends(get_db)):
    """获取通知配置"""
    return NotificationConfigResponse(
        email_enabled=get_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_ENABLED, False) == "true",
        email_smtp_host=get_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_HOST),
        email_smtp_port=int(get_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_PORT, 587) or 587),
        email_smtp_user=get_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_USER),
        email_smtp_password=None,  # 不返回密码
        email_smtp_tls=get_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_TLS, "true") == "true",
        email_from=get_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_FROM),
        email_from_name=get_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_FROM_NAME),
        webhook_enabled=get_config_value(db, ConfigCategory.WEBHOOK, ConfigKey.WEBHOOK_ENABLED, False) == "true",
        webhook_url=get_config_value(db, ConfigCategory.WEBHOOK, ConfigKey.WEBHOOK_URL),
        webhook_secret=None,  # 不返回密钥
        webhook_timeout=int(get_config_value(db, ConfigCategory.WEBHOOK, ConfigKey.WEBHOOK_TIMEOUT, 10) or 10),
    )


@router.put("/notification", response_model=NotificationConfigResponse)
def update_notification_config(
    config: NotificationConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新通知配置"""
    # 邮件配置
    set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_ENABLED, str(config.email_enabled).lower(), "启用邮件通知")
    if config.email_smtp_host:
        set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_HOST, config.email_smtp_host, "SMTP 服务器地址")
    set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_PORT, str(config.email_smtp_port), "SMTP 端口")
    if config.email_smtp_user:
        set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_USER, config.email_smtp_user, "SMTP 用户名")
    if config.email_smtp_password:
        set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_PASSWORD, config.email_smtp_password, "SMTP 密码", is_secret=True)
    set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_SMTP_TLS, str(config.email_smtp_tls).lower(), "启用 TLS")
    if config.email_from:
        set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_FROM, config.email_from, "发件人邮箱")
    if config.email_from_name:
        set_config_value(db, ConfigCategory.EMAIL, ConfigKey.EMAIL_FROM_NAME, config.email_from_name, "发件人名称")
    
    # Webhook 配置
    set_config_value(db, ConfigCategory.WEBHOOK, ConfigKey.WEBHOOK_ENABLED, str(config.webhook_enabled).lower(), "启用 Webhook 通知")
    if config.webhook_url:
        set_config_value(db, ConfigCategory.WEBHOOK, ConfigKey.WEBHOOK_URL, config.webhook_url, "Webhook URL")
    if config.webhook_secret:
        set_config_value(db, ConfigCategory.WEBHOOK, ConfigKey.WEBHOOK_SECRET, config.webhook_secret, "Webhook 密钥", is_secret=True)
    set_config_value(db, ConfigCategory.WEBHOOK, ConfigKey.WEBHOOK_TIMEOUT, str(config.webhook_timeout), "Webhook 超时（秒）")
    
    # 返回更新后的配置
    return get_notification_config(db)


@router.get("/mcp", response_model=MCPConfigResponse)
def get_mcp_config(db: Session = Depends(get_db)):
    """获取 MCP 配置"""
    return MCPConfigResponse(
        mcp_enabled=get_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_ENABLED, "false") == "true",
        mcp_server_command=get_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_SERVER_COMMAND, "npx"),
        mcp_server_args=get_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_SERVER_ARGS, "-y @modelcontextprotocol/server-playwright"),
        mcp_server_url=get_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_SERVER_URL),
        mcp_max_retries=int(get_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_MAX_RETRIES, 3) or 3),
        mcp_timeout=int(get_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_TIMEOUT, 30) or 30),
    )


@router.put("/mcp", response_model=MCPConfigResponse)
def update_mcp_config(
    config: MCPConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新 MCP 配置"""
    set_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_ENABLED, str(config.mcp_enabled).lower(), "启用 MCP 执行模式")
    set_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_SERVER_COMMAND, config.mcp_server_command, "MCP 服务器命令")
    set_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_SERVER_ARGS, config.mcp_server_args, "MCP 服务器参数")
    if config.mcp_server_url:
        set_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_SERVER_URL, config.mcp_server_url, "MCP 服务器 URL")
    set_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_MAX_RETRIES, str(config.mcp_max_retries), "最大重试次数")
    set_config_value(db, ConfigCategory.MCP, ConfigKey.MCP_TIMEOUT, str(config.mcp_timeout), "超时时间（秒）")
    
    return get_mcp_config(db)


@router.post("/", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
def create_config(
    config: ConfigCreate,
    db: Session = Depends(get_db)
):
    """创建配置"""
    # 检查是否已存在
    existing = db.query(SystemConfig).filter(
        SystemConfig.category == config.category,
        SystemConfig.key == config.key
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置已存在: {config.category}/{config.key}"
        )
    
    db_config = SystemConfig(
        category=config.category,
        key=config.key,
        description=config.description,
        is_secret=config.is_secret,
        is_active=config.is_active
    )
    
    if config.value_json is not None:
        db_config.value_json = config.value_json
    else:
        db_config.value = config.value
    
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config


@router.put("/{config_id}", response_model=ConfigResponse)
def update_config(
    config_id: UUID,
    config: ConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新配置"""
    db_config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    if config.value is not None:
        db_config.value = config.value
        db_config.value_json = None
    if config.value_json is not None:
        db_config.value_json = config.value_json
        db_config.value = None
    if config.description is not None:
        db_config.description = config.description
    if config.is_secret is not None:
        db_config.is_secret = config.is_secret
    if config.is_active is not None:
        db_config.is_active = config.is_active
    
    db.commit()
    db.refresh(db_config)
    
    return db_config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(
    config_id: UUID,
    db: Session = Depends(get_db)
):
    """删除配置"""
    db_config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    db.delete(db_config)
    db.commit()
