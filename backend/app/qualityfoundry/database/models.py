"""QualityFoundry - Database Models

SQLAlchemy 数据模型定义
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.ext.declarative import declarative_base # Removed
from sqlalchemy.orm import relationship

from qualityfoundry.database.config import Base


# ============================================================
# 枚举类型
# ============================================================

class RequirementStatus(str, PyEnum):
    """需求状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ApprovalStatus(str, PyEnum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExecutionStatus(str, PyEnum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"


class ExecutionMode(str, PyEnum):
    """执行模式"""
    DSL = "dsl"
    MCP = "mcp"
    HYBRID = "hybrid"


# ============================================================
# 数据模型
# ============================================================

class Requirement(Base):
    """需求模型"""
    __tablename__ = "requirements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)  # 需求文档内容
    file_path = Column(String(512), nullable=True)  # 上传文件路径
    version = Column(String(50), nullable=False, default="v1.0")  # 版本号
    status = Column(Enum(RequirementStatus), nullable=False, default=RequirementStatus.DRAFT)
    created_by = Column(String(100), nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    scenarios = relationship("Scenario", back_populates="requirement", cascade="all, delete-orphan")


class Scenario(Base):
    """测试场景模型"""
    __tablename__ = "scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    steps = Column(JSON, nullable=False, default=list)  # 场景步骤（JSON 数组）
    approval_status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(String(50), nullable=False, default="v1.0")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    requirement = relationship("Requirement", back_populates="scenarios")
    testcases = relationship("TestCase", back_populates="scenario", cascade="all, delete-orphan")


class TestCase(Base):
    """测试用例模型"""
    __tablename__ = "testcases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=False)
    title = Column(String(255), nullable=False)
    preconditions = Column(JSON, nullable=False, default=list)  # 前置条件（JSON 数组）
    steps = Column(JSON, nullable=False, default=list)  # 测试步骤（JSON 数组）
    expected_results = Column(JSON, nullable=False, default=list)  # 预期结果（JSON 数组）
    approval_status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(String(50), nullable=False, default="v1.0")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    scenario = relationship("Scenario", back_populates="testcases")
    executions = relationship("Execution", back_populates="testcase", cascade="all, delete-orphan")


class Environment(Base):
    """环境配置模型"""
    __tablename__ = "environments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)  # dev/sit/uat/prod
    base_url = Column(String(512), nullable=False)
    variables = Column(JSON, nullable=False, default=dict)  # 环境变量（JSON 对象）
    credentials = Column(Text, nullable=True)  # 凭证（加密存储）
    health_check_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    executions = relationship("Execution", back_populates="environment")


class Execution(Base):
    """执行记录模型"""
    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    testcase_id = Column(UUID(as_uuid=True), ForeignKey("testcases.id"), nullable=False)
    environment_id = Column(UUID(as_uuid=True), ForeignKey("environments.id"), nullable=False)
    mode = Column(Enum(ExecutionMode), nullable=False, default=ExecutionMode.DSL)
    status = Column(Enum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    artifact_dir = Column(String(512), nullable=True)  # 证据目录
    evidence = Column(JSON, nullable=False, default=list)  # 证据列表（JSON 数组）
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # 关联
    testcase = relationship("TestCase", back_populates="executions")
    environment = relationship("Environment", back_populates="executions")


class Approval(Base):
    """审核记录模型"""
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)  # scenario/testcase
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    reviewer = Column(String(100), nullable=True)
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ReportType(str, PyEnum):
    """报表类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


class Report(Base):
    """测试报告模型"""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    type = Column(Enum(ReportType), nullable=False, default=ReportType.ON_DEMAND)
    data = Column(JSON, nullable=False, default=dict)  # 统计数据
    file_path = Column(String(512), nullable=True)     # PDF/HTML 文件路径
    created_by = Column(String(100), nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Upload(Base):
    """上传文件记录"""
    __tablename__ = "uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    size = Column(Integer, nullable=True)
    path = Column(String(512), nullable=False)
    uploaded_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
