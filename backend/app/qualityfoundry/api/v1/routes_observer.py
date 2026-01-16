from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from qualityfoundry.database.config import get_db
from qualityfoundry.services.observer_service import ObserverService, ObserverError
from qualityfoundry.models.observer_schemas import (
    ConsistencyResponse,
    CoverageResponse,
    GodSuggestionsResponse
)

router = APIRouter()

@router.get("/consistency/{requirement_id}", response_model=ConsistencyResponse)
async def analyze_consistency(
    requirement_id: UUID,
    config_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """分析全链路一致性"""
    try:
        result = await ObserverService.analyze_consistency(db, requirement_id, config_id)
        return result
    except ObserverError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/coverage/{requirement_id}", response_model=CoverageResponse)
async def evaluate_coverage(
    requirement_id: UUID,
    config_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """评估覆盖度"""
    try:
        result = await ObserverService.evaluate_coverage(db, requirement_id, config_id)
        return result
    except ObserverError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/suggestions/{requirement_id}", response_model=GodSuggestionsResponse)
async def get_god_suggestions(
    requirement_id: UUID,
    config_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取上帝建议"""
    try:
        result = await ObserverService.get_god_suggestions(db, requirement_id, config_id)
        return result
    except ObserverError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
