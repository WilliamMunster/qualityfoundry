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

    model_config = ConfigDict(from_attributes=True)


class AITestRequest(BaseModel):
    """AI 测试请求"""
    config_id: UUID
    prompt: str


class AITestResponse(BaseModel):
    """AI 测试响应"""
    success: bool
    response: Optional[str]
    error: Optional[str]
