"""QualityFoundry - AI Prompt Management Routes

AI 提示词配置管理
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from qualityfoundry.database.config import get_db
from qualityfoundry.database.ai_config_models import AIPrompt
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/ai-prompts", tags=["ai-prompts"])

class AIPromptBase(BaseModel):
    step: str
    name: str
    system_prompt: str
    user_prompt: str

class AIPromptResponse(AIPromptBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[AIPromptResponse])
def list_prompts(db: Session = Depends(get_db)):
    """获取所有提示词配置"""
    return db.query(AIPrompt).all()

@router.get("/{step}", response_model=AIPromptResponse)
def get_prompt_by_step(step: str, db: Session = Depends(get_db)):
    """根据步骤获取提示词"""
    prompt = db.query(AIPrompt).filter(AIPrompt.step == step).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt configuration not found")
    return prompt

@router.put("/{step}", response_model=AIPromptResponse)
def update_prompt(step: str, req: AIPromptBase, db: Session = Depends(get_db)):
    """更新提示词配置"""
    prompt = db.query(AIPrompt).filter(AIPrompt.step == step).first()
    if not prompt:
        # 如果不存在则创建
        prompt = AIPrompt(step=step)
        db.add(prompt)
    
    prompt.name = req.name
    prompt.system_prompt = req.system_prompt
    prompt.user_prompt = req.user_prompt
    
    db.commit()
    db.refresh(prompt)
    return prompt

@router.post("/seed", status_code=201)
def seed_default_prompts(db: Session = Depends(get_db)):
    """注入默认提示词 (Seed)"""
    from qualityfoundry.services.ai_service import FALLBACK_PROMPTS
    
    count = 0
    for step, content in FALLBACK_PROMPTS.items():
        existing = db.query(AIPrompt).filter(AIPrompt.step == step.value).first()
        if not existing:
            prompt = AIPrompt(
                step=step.value,
                name=f"默认{step.value}提示词",
                system_prompt=content["system"],
                user_prompt=content["user"]
            )
            db.add(prompt)
            count += 1
    
    db.commit()
    return {"message": f"Successfully seeded {count} prompts"}
