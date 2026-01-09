"""QualityFoundry - Environment API Routes

环境管理 API 路由
"""
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import Environment
from qualityfoundry.models.environment_schemas import (
    EnvironmentCreate,
    EnvironmentListResponse,
    EnvironmentResponse,
    EnvironmentUpdate,
    HealthCheckResponse,
)
from qualityfoundry.services.encryption_service import encryption_service

router = APIRouter(prefix="/environments", tags=["environments"])


@router.post("", response_model=EnvironmentResponse, status_code=201)
def create_environment(
    req: EnvironmentCreate,
    db: Session = Depends(get_db)
):
    """创建环境"""
    # 检查名称是否已存在
    existing = db.query(Environment).filter(Environment.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"环境名称已存在: {req.name}")
    
    # 加密凭证
    encrypted_credentials = None
    if req.credentials:
        encrypted_credentials = encryption_service.encrypt(req.credentials)
    
    environment = Environment(
        name=req.name,
        base_url=req.base_url,
        variables=req.variables,
        credentials=encrypted_credentials,
        health_check_url=req.health_check_url,
        is_active=True
    )
    
    db.add(environment)
    db.commit()
    db.refresh(environment)
    
    return environment


@router.get("", response_model=EnvironmentListResponse)
def list_environments(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """环境列表"""
    query = db.query(Environment)
    
    # 按激活状态筛选
    if is_active is not None:
        query = query.filter(Environment.is_active == is_active)
    
    items = query.order_by(Environment.created_at.desc()).all()
    
    return EnvironmentListResponse(
        total=len(items),
        items=items
    )


@router.get("/{environment_id}", response_model=EnvironmentResponse)
def get_environment(
    environment_id: UUID,
    db: Session = Depends(get_db)
):
    """环境详情"""
    environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    return environment


@router.put("/{environment_id}", response_model=EnvironmentResponse)
def update_environment(
    environment_id: UUID,
    req: EnvironmentUpdate,
    db: Session = Depends(get_db)
):
    """更新环境"""
    environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    # 更新字段
    if req.base_url is not None:
        environment.base_url = req.base_url
    if req.variables is not None:
        environment.variables = req.variables
    if req.credentials is not None:
        # 加密凭证
        environment.credentials = encryption_service.encrypt(req.credentials)
    if req.health_check_url is not None:
        environment.health_check_url = req.health_check_url
    if req.is_active is not None:
        environment.is_active = req.is_active
    
    db.commit()
    db.refresh(environment)
    return environment


@router.delete("/{environment_id}", status_code=204)
def delete_environment(
    environment_id: UUID,
    db: Session = Depends(get_db)
):
    """删除环境"""
    environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    db.delete(environment)
    db.commit()
    return None


@router.post("/{environment_id}/health-check", response_model=HealthCheckResponse)
async def health_check(
    environment_id: UUID,
    db: Session = Depends(get_db)
):
    """环境健康检查"""
    environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    # 确定健康检查 URL
    check_url = environment.health_check_url or environment.base_url
    
    # 执行健康检查
    is_healthy = False
    status_code = None
    response_time_ms = None
    error_message = None
    
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(check_url)
            response_time_ms = (time.time() - start_time) * 1000
            status_code = response.status_code
            is_healthy = 200 <= status_code < 300
    except Exception as e:
        error_message = str(e)
        is_healthy = False
    
    return HealthCheckResponse(
        environment_id=environment.id,
        environment_name=environment.name,
        is_healthy=is_healthy,
        status_code=status_code,
        response_time_ms=response_time_ms,
        error_message=error_message,
        checked_at=datetime.now(timezone.utc)
    )
