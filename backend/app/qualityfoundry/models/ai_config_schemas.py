"""QualityFoundry - AI Config Schemas

AI 配置 Pydantic 模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AIConfigCreate(BaseModel):
    """创建 AI 配置"""
    name: str
    provider: str  # openai, deepseek, anthropic, etc.
    model: str
    api_key: str
    base_url: Optional[str] = None
    assigned_steps: Optional[List[str]] = None
    temperature: str = "0.7"
    max_tokens: str = "2000"
    top_p: str = "1.0"
    extra_params: Optional[Dict[str, Any]] = None
    is_default: bool = False


class AIConfigUpdate(BaseModel):
    """更新 AI 配置"""
    name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    assigned_steps: Optional[List[str]] = None
    temperature: Optional[str] = None
    max_tokens: Optional[str] = None
    top_p: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class AIConfigResponse(BaseModel):
    """AI 配置响应"""
    id: UUID
    name: str
    provider: str
    model: str
    base_url: Optional[str]
    assigned_steps: Optional[List[str]]
    temperature: str
    max_tokens: str
    top_p: str
    extra_params: Optional[Dict[str, Any]]
    is_active: bool
    is_default: bool
    created_at: datetime
    api_key_masked: Optional[str] = None  # 掩码后的 API Key

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_mask(cls, obj):
        """从 ORM 对象创建响应，并添加掩码 API Key"""
        data = {
            "id": obj.id,
            "name": obj.name,
            "provider": obj.provider,
            "model": obj.model,
            "base_url": obj.base_url,
            "assigned_steps": obj.assigned_steps,
            "temperature": obj.temperature,
            "max_tokens": obj.max_tokens,
            "top_p": obj.top_p,
            "extra_params": obj.extra_params,
            "is_active": obj.is_active,
            "is_default": obj.is_default,
            "created_at": obj.created_at,
            "api_key_masked": cls._mask_api_key(obj.api_key) if obj.api_key else None,
        }
        return cls(**data)
    
    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """将 API Key 掩码处理，只显示前4位和后4位"""
        if not api_key or len(api_key) < 12:
            return "****已配置****"
        return f"{api_key[:4]}****...****{api_key[-4:]}"


class AITestRequest(BaseModel):
    """AI 测试请求"""
    config_id: Optional[UUID] = None
    prompt: str = "Hello"
    
    # Transient config params (for testing before saving)
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class AITestResponse(BaseModel):
    """AI 测试响应"""
    success: bool
    response: Optional[str]
    error: Optional[str]


class AIExecutionLogResponse(BaseModel):
    """AI 执行日志响应"""
    id: UUID
    step: Optional[str]
    config_id: Optional[UUID]
    provider: Optional[str]
    model: Optional[str]
    request_messages: Optional[List[Dict[str, Any]]]
    response_content: Optional[str]
    status: str
    error_message: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
