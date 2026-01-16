"""QualityFoundry - AI Config Routes

AI 配置管理 API 路由
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.ai_config_models import AIConfig
from qualityfoundry.models.ai_config_schemas import (
    AIConfigCreate,
    AIConfigUpdate,
    AIConfigResponse,
    AITestRequest,
    AITestResponse,
    AIExecutionLogResponse,
)
from qualityfoundry.services.ai_service import AIService

router = APIRouter(prefix="/ai-configs", tags=["ai-configs"])


@router.post("", response_model=AIConfigResponse, status_code=201)
def create_ai_config(config_data: AIConfigCreate, db: Session = Depends(get_db)):
    """创建 AI 配置"""
    # 如果设置为默认，取消其他默认配置
    if config_data.is_default:
        db.query(AIConfig).filter(AIConfig.is_default).update(
            {"is_default": False}
        )
    
    # 创建新配置
    new_config = AIConfig(
        name=config_data.name,
        provider=config_data.provider,
        model=config_data.model,
        api_key=config_data.api_key,
        base_url=config_data.base_url,
        assigned_steps=config_data.assigned_steps,
        temperature=config_data.temperature,
        max_tokens=config_data.max_tokens,
        top_p=config_data.top_p,
        extra_params=config_data.extra_params,
        is_default=config_data.is_default,
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return AIConfigResponse.from_orm_with_mask(new_config)


@router.get("", response_model=list[AIConfigResponse])
def list_ai_configs(
    is_active: Optional[bool] = None,
    provider: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """AI 配置列表"""
    query = db.query(AIConfig)
    
    if is_active is not None:
        query = query.filter(AIConfig.is_active == is_active)
    
    if provider:
        query = query.filter(AIConfig.provider == provider)
    
    configs = query.all()
    return [AIConfigResponse.from_orm_with_mask(c) for c in configs]


@router.get("/logs", response_model=list[AIExecutionLogResponse])
def list_ai_logs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    step: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """AI 执行日志列表"""
    from qualityfoundry.database.ai_config_models import AIExecutionLog
    query = db.query(AIExecutionLog)
    
    if status:
        query = query.filter(AIExecutionLog.status == status)
    if step:
        query = query.filter(AIExecutionLog.step == step)
        
    logs = query.order_by(AIExecutionLog.created_at.desc()).offset(offset).limit(limit).all()
    return logs


@router.get("/{config_id}", response_model=AIConfigResponse)
def get_ai_config(config_id: UUID, db: Session = Depends(get_db)):
    """获取 AI 配置详情"""
    config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return AIConfigResponse.from_orm_with_mask(config)


@router.put("/{config_id}", response_model=AIConfigResponse)
def update_ai_config(
    config_id: UUID,
    config_data: AIConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新 AI 配置"""
    config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    # 如果设置为默认，取消其他默认配置
    if config_data.is_default:
        db.query(AIConfig).filter(
            AIConfig.id != config_id,
            AIConfig.is_default
        ).update({"is_default": False})
    
    # 更新字段
    if config_data.name is not None:
        config.name = config_data.name
    if config_data.provider is not None:
        config.provider = config_data.provider
    if config_data.model is not None:
        config.model = config_data.model
    if config_data.api_key is not None:
        config.api_key = config_data.api_key
    if config_data.base_url is not None:
        config.base_url = config_data.base_url
    if config_data.assigned_steps is not None:
        config.assigned_steps = config_data.assigned_steps
    if config_data.temperature is not None:
        config.temperature = config_data.temperature
    if config_data.max_tokens is not None:
        config.max_tokens = config_data.max_tokens
    if config_data.top_p is not None:
        config.top_p = config_data.top_p
    if config_data.extra_params is not None:
        config.extra_params = config_data.extra_params
    if config_data.is_active is not None:
        config.is_active = config_data.is_active
    if config_data.is_default is not None:
        config.is_default = config_data.is_default
    
    db.commit()
    db.refresh(config)
    
    return AIConfigResponse.from_orm_with_mask(config)


@router.delete("/{config_id}")
def delete_ai_config(config_id: UUID, db: Session = Depends(get_db)):
    """删除 AI 配置"""
    config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    db.delete(config)
    db.commit()
    
    return {"message": "配置已删除"}


@router.post("/test", response_model=AITestResponse)
async def test_ai_config(test_data: AITestRequest, db: Session = Depends(get_db)):
    """测试 AI 配置"""
    config = None
    
    if test_data.config_id:
        # 获取基础配置
        config_obj = db.query(AIConfig).filter(AIConfig.id == test_data.config_id).first()
        if not config_obj:
            raise HTTPException(status_code=404, detail="配置不存在")
        
        # 使用表单中的新参数覆盖现有配置（仅用于本次测试，不保存）
        config = AIConfig(
            id=config_obj.id,
            name=config_obj.name,
            provider=test_data.provider or config_obj.provider,
            model=test_data.model or config_obj.model,
            api_key=test_data.api_key or config_obj.api_key,
            base_url=test_data.base_url if test_data.base_url is not None else config_obj.base_url,
            temperature=config_obj.temperature,
            max_tokens=config_obj.max_tokens,
            top_p=config_obj.top_p
        )
    elif test_data.provider and test_data.api_key and test_data.model:
        # 纯临时配置测试
        config = AIConfig(
            name="Test Config",
            provider=test_data.provider,
            model=test_data.model,
            api_key=test_data.api_key,
            base_url=test_data.base_url,
            temperature="0.7",
            max_tokens="100",
            top_p="1.0"
        )
    else:
        raise HTTPException(
            status_code=400, 
            detail="测试失败：必须提供有效的 config_id 或完整的配置参数 (提供商、模型、API Key)"
        )
    
    result = await AIService.test_config(config, test_data.prompt)
    
    return AITestResponse(**result)


