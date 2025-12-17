from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# --------------------------
# Test Asset Schemas
# --------------------------

class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class CaseStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    FINAL = "final"


class RequirementInput(BaseModel):
    title: str = Field(..., min_length=1, description="Requirement title")
    text: str = Field(..., min_length=1, description="Raw requirement text (PRD/user story/spec)")
    domain: Optional[str] = Field(default=None, description="Optional business domain")


class TestModule(BaseModel):
    id: str = Field(..., description="Stable ID (uuid or slug)")
    name: str
    description: str | None = None


class TestObjective(BaseModel):
    id: str
    module_id: str
    name: str
    description: str | None = None


class TestPoint(BaseModel):
    id: str
    objective_id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class TestStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step: str = Field(..., description="Action step in natural language")
    expected: str = Field(..., description="Expected result, must correspond 1:1 with step")


class TestCase(BaseModel):
    id: str
    objective_id: str
    title: str
    preconditions: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.P1
    tags: list[str] = Field(default_factory=list)
    steps: list[TestStep] = Field(..., min_length=1)
    status: CaseStatus = CaseStatus.DRAFT


class CaseBundle(BaseModel):
    requirement: RequirementInput
    modules: list[TestModule]
    objectives: list[TestObjective]
    test_points: list[TestPoint]
    cases: list[TestCase]


# --------------------------
# Execution DSL Schemas
# --------------------------

class Locator(BaseModel):
    """A controlled locator abstraction. Prefer stable strategies first."""
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["role", "label", "text", "testid", "css", "xpath"] = "role"
    value: str = Field(..., min_length=1)
    role: Optional[str] = None  # when strategy == role
    exact: bool = False


class ActionType(str, Enum):
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    WAIT = "wait"
    ASSERT_TEXT = "assert_text"
    ASSERT_VISIBLE = "assert_visible"


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ActionType
    locator: Optional[Locator] = None
    url: Optional[str] = None
    value: Optional[str] = None
    timeout_ms: int = 15000


class ExecutionResponse(BaseModel):
    """
    Execute / Execute Bundle 的通用执行结果结构。
    目标：让接口返回具备一致的“执行摘要 + evidence”能力，便于后续生成报告。
    """
    ok: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifact_dir: str | None = None
    evidence: list["StepEvidence"] = Field(default_factory=list)


class ExecutionRequest(BaseModel):
    base_url: str | None = None
    actions: list[Action]
    headless: bool = True


class StepEvidence(BaseModel):
    index: int
    action: Action | None = None
    ok: bool
    screenshot: str | None = None
    error: str | None = None


class ExecutionResult(BaseModel):
    ok: bool
    started_at: str
    finished_at: str
    artifact_dir: str
    evidence: list[StepEvidence]


# -----------------------------
# Execute Bundle（一键：bundle -> compile -> execute）
# -----------------------------


class ExecuteBundleCompileOptions(BaseModel):
    """
    编译选项（与 compile_bundle 的 options 对齐）
    - target 预留：未来可支持不同编译目标（如 playwright_dsl_v1 / selenium_dsl_v1）
    - strict=True：出现任何无法编译步骤即失败（更利于 CI 稳定）
    """
    target: str = "playwright_dsl_v1"
    strict: bool = True
    default_timeout_ms: int = 15000


class ExecuteBundleRunOptions(BaseModel):
    """
    执行选项：
    - base_url：用于执行上下文/相对路径/回归一致性（为空时会从 actions 推断）
    - headless：CI 默认 True
    """
    base_url: Optional[str] = None
    headless: bool = True


class ExecuteBundleCompiledCase(BaseModel):
    """
    返回给调用方的“编译结果”（方便调试）：
    - actions：最终下发给执行器的 DSL
    - warnings：编译阶段的告警（strict=False 时可能存在）
    """
    case_id: str
    title: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExecuteBundleRequest(BaseModel):
    """
    一键执行请求：
    - bundle：来自 /generate 的完整输出
    - case_index：要执行 bundle 中第几条 case（默认 0）
    - compile_options/run：可选覆盖
    """
    bundle: "CaseBundle"
    case_index: int = 0
    compile_options: ExecuteBundleCompileOptions = Field(default_factory=ExecuteBundleCompileOptions)
    run: ExecuteBundleRunOptions = Field(default_factory=ExecuteBundleRunOptions)


class ExecuteBundleResponse(BaseModel):
    """
    一键执行响应：
    - ok：整体是否成功（以 execution.ok 为准）
    - compiled：可选返回编译后的 actions 便于排查（默认返回）
    - execution：执行结果（证据、artifact_dir）
    - error：失败原因概述（更适合前端直接显示）
    """
    ok: bool
    compiled: Optional[ExecuteBundleCompiledCase] = None
    execution: dict[str, Any]
    error: Optional[str] = None
