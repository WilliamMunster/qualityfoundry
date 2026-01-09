"""QualityFoundry - File Upload Service

文件上传与解析服务
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile


class FileUploadService:
    """文件上传服务"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的文件类型
        self.allowed_extensions = {".pdf", ".docx", ".doc", ".md", ".txt"}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    async def save_file(self, file: UploadFile) -> tuple[str, str]:
        """
        保存上传的文件
        
        Returns:
            (file_path, original_filename)
        """
        # 检查文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise ValueError(f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(self.allowed_extensions)}")
        
        # 生成唯一文件名
        unique_filename = f"{uuid4()}{file_ext}"
        file_path = self.upload_dir / unique_filename
        
        # 保存文件
        content = await file.read()
        
        # 检查文件大小
        if len(content) > self.max_file_size:
            raise ValueError(f"文件过大: {len(content)} bytes。最大允许: {self.max_file_size} bytes")
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return str(file_path), file.filename
    
    def extract_text(self, file_path: str) -> str:
        """
        从文件中提取文本内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        if file_ext == ".txt" or file_ext == ".md":
            # 纯文本文件
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif file_ext == ".pdf":
            # PDF 文件（需要 PyPDF2 或 pdfplumber）
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                return "[PDF 文件 - 需要安装 PyPDF2 库来提取文本]"
        
        elif file_ext in [".docx", ".doc"]:
            # Word 文件（需要 python-docx）
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                return "[Word 文件 - 需要安装 python-docx 库来提取文本]"
        
        else:
            return f"[不支持的文件类型: {file_ext}]"
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功删除
        """
        try:
            Path(file_path).unlink()
            return True
        except Exception:
            return False


# 全局实例
file_upload_service = FileUploadService()
