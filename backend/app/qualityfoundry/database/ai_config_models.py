"""QualityFoundry - AI Config Models

AI 模型配置数据模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from qualityfoundry.database.config import Base


class AIStep(str, enum.Enum):
    """AI 执行步骤"""
    REQUIREMENT_ANALYSIS = "requirement_analysis"  # 需求分析 → 场景
    SCENARIO_GENERATION = "scenario_generation"    # 场景生成
    TESTCASE_GENERATION = "testcase_generation"    # 场景 → 用例
    CODE_GENERATION = "code_generation"            # 代码生成
    REVIEW = "review"                              # 审核建议


class AIConfig(Base):
    """AI 模型配置"""
    __tablename__ = "ai_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)  # 配置名称
    provider = Column(String(50), nullable=False)  # 提供商：openai, deepseek, anthropic 等
    model = Column(String(100), nullable=False)  # 模型名称
    api_key = Column(String(500), nullable=False)  # API Key（加密存储）
    base_url = Column(String(500), nullable=True)  # 自定义 Base URL
    
    # 步骤绑定
    assigned_steps = Column(JSON, nullable=True)  # 分配的步骤列表
    
    # 模型参数
    temperature = Column(String(10), default="0.7")
    max_tokens = Column(String(10), default="2000")
    top_p = Column(String(10), default="1.0")
    
    # 其他配置
    extra_params = Column(JSON, nullable=True)  # 额外参数
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)  # 是否为默认配置
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
