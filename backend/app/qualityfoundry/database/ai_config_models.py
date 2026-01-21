"""QualityFoundry - AI Config Models

AI 模型配置数据模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text, Integer
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
    EXECUTION_ANALYSIS = "execution_analysis"      # 执行结果分析
    GLOBAL_OBSERVER = "global_observer"            # 上帝视角 - 全链路监督


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


class AIPrompt(Base):
    """AI 提示词配置"""
    __tablename__ = "ai_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step = Column(String(50), nullable=False, unique=True)  # 对应 AIStep
    name = Column(String(100), nullable=False)  # 场景描述
    system_prompt = Column(Text, nullable=True)  # 系统提示词
    user_prompt = Column(Text, nullable=False)    # 用户提示词模板
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AIExecutionLog(Base):
    """AI 执行日志"""
    __tablename__ = "ai_execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step = Column(String(50), nullable=True)  # 对应 AIStep
    config_id = Column(UUID(as_uuid=True), nullable=True) # 使用的配置ID
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    
    request_messages = Column(JSON, nullable=True) # 完整请求消息列表
    response_content = Column(Text, nullable=True) # AI 响应内容
    
    status = Column(String(20), nullable=False) # success, failed
    error_message = Column(Text, nullable=True) # 错误信息
    
    duration_ms = Column(Integer, nullable=True) # 执行耗时 (毫秒)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
