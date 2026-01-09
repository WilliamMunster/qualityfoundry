"""QualityFoundry - File Upload Routes

文件上传 API 路由
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from pathlib import Path
from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import Requirement
from qualityfoundry.models.requirement_schemas import RequirementResponse
from qualityfoundry.services.file_upload import file_upload_service

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/requirement", response_model=RequirementResponse, status_code=201)
async def upload_requirement_file(
    file: UploadFile = File(...),
    title: str = None,
    db: Session = Depends(get_db)
):
    """
    上传需求文档文件
    
    支持的文件类型：PDF、Word、Markdown、TXT
    最大文件大小：10MB
    """
    try:
        # 保存文件
        file_path, original_filename = await file_upload_service.save_file(file)
        
        # 提取文本内容
        content = file_upload_service.extract_text(file_path)
        
        # 创建需求记录
        requirement = Requirement(
            title=title or original_filename,
            content=content,
            file_path=file_path,
            version="v1.0",
            created_by="system"
        )
        
        db.add(requirement)
        
        # [NEW] 创建通用上传记录
        from qualityfoundry.database.models import Upload
        upload_record = Upload(
            filename=str(Path(file_path).name),
            original_name=original_filename,
            content_type=file.content_type,
            size=file.size, # Note: file.size might not be available depending on spooling, but usually is
            path=file_path,
            uploaded_by="system"
        )
        db.add(upload_record)
        
        db.commit()
        db.refresh(requirement)
        
        return requirement
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
