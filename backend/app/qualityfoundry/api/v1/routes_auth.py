"""QualityFoundry - 认证相关路由

提供登出等认证管理功能。
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout")
def logout(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """用户登出（撤销 token）
    
    撤销当前 token，使其立即失效。
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证信息")
    
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="无效的认证信息")
    
    success = AuthService.revoke_token(db, token)
    
    if not success:
        raise HTTPException(status_code=401, detail="Token 无效或已撤销")
    
    return {"message": "已成功登出"}
