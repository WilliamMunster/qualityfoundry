"""QualityFoundry - Pydantic Schemas（数据契约）

说明：
- 本文件定义系统对外/对内的数据结构（API 请求/响应、测试资产、DSL、执行结果等）
- 约束：imports 必须位于文件顶部（ruff E402）
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# 1) Test Asset Schemas（结构化测试资产）
# ============================================================

class Priority(str, Enum):
    """用例优先级（用于筛选/冒烟/回归分层）"""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class CaseStatus(str, Enum):
    """用例状态（草稿/已评审/定版）"""
    DRAFT = "draft"
    REVIEWED = "reviewed"
    FINAL = "final"


class RequirementInput(BaseModel):
    """输入：原始需求文本（PRD/用户故事/说明文档片段）"""
    title: str = Field(..., min_length=1, description="Requirement title")
    text: str = Field(..., min_length=1, description="Raw requirement text (PRD/user story/spec)")
    domain: Optional[str] = Field(default=None, description="Optional business domain")


class TestModule(BaseModel):
    """测试模块（一级分类）"""
    id: str = Field(..., description="Stable ID (uuid or slug)")
    name: str
    description: str | None = None


class TestObjective(BaseModel):
    """测试目标（模块下的二级分类）"""
    id: str
    module_id: str
    name: str
    description: str | None = None


class TestPoint(BaseModel):
    """测试点（目标下的测试覆盖点）"""
    id: str
    objective_id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class TestStep(BaseModel):
    """步骤：step / expected 1:1 对齐"""
    model_config = ConfigDict(extra="forbid")

    step: str = Field(..., description="Action step in natural language")
    expected: str = Field(..., description="Expected result, must correspond 1:1 with step")


class TestCase(BaseModel):
    """用例：结构化测试资产中的可执行单元（自然语言步骤）"""
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
    """生成结果：一份需求对应的一组结构化测试资产"""
    requirement: RequirementInput
    modules: list[TestModule]
    objectives: list[TestObjective]
    test_points: list[TestPoint]
    cases: list[TestCase]


# ============================================================
# 2) Execution DSL Schemas（确定性执行 DSL）
# ============================================================

class Locator(BaseModel):
    """受控定位器抽象：优先稳定策略（role/label/testid），再到 text/css/xpath"""
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["role", "label", "text", "placeholder", "testid", "css", "xpath"] = "role"
    value: str = Field(..., min_length=1)
    role: Optional[str] = None  # when strategy == role
    exact: bool = False



class ActionType(str, Enum):
    """动作类型：逐步扩充，但要保持语义稳定"""
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
    """单步 DSL 动作（Compile 的输出 / Execute 的输入）"""
    model_config = ConfigDict(extra="forbid")

    type: ActionType
    locator: Optional[Locator] = None
    url: Optional[str] = None
    value: Optional[str] = None
    timeout_ms: int = 15000


class ExecutionRequest(BaseModel):
    """执行请求：给 runner 的 DSL actions"""
    base_url: str | None = None
    actions: list[Action]
    headless: bool = True


class StepEvidence(BaseModel):
    """单步证据：用于报告/溯源"""
    index: int
    action: Action | None = None
    ok: bool
    screenshot: str | None = None
    error: str | None = None


class ExecutionResponse(BaseModel):
    """
    统一的执行返回结构（单条执行结果）。
    - ok：整体是否成功
    - started_at/finished_at：UTC 或本地均可，但建议服务端统一输出 UTC
    - artifact_dir：产物目录（截图、log、trace 等）
    - evidence：逐步证据
    """
    ok: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifact_dir: str | None = None
    evidence: list[StepEvidence] = Field(default_factory=list)


# 兼容旧命名：历史代码可能还在使用 ExecutionResult
# 不再定义第二套结构，避免“同名不同字段”造成长期维护灾难
ExecutionResult = ExecutionResponse


# ============================================================
# 3) Compile Bundle（bundle -> compiled actions）
#    注：如果你已有单独的 compile_bundle 契约，可以按需保留/迁移
# ============================================================

class CompileOptions(BaseModel):
    """编译选项（与 /compile_bundle 对齐）"""
    target: Literal["playwright_dsl_v1"] = "playwright_dsl_v1"
    strict: bool = True
    default_timeout_ms: int = 15000


class CompiledCase(BaseModel):
    """单条用例编译结果（供调试/执行）"""
    case_id: str
    title: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CompileBundleRequest(BaseModel):
    """编译 bundle 请求：通常来自 /generate 的 bundle 输出"""
    requirement: RequirementInput
    modules: list[TestModule]
    objectives: list[TestObjective]
    test_points: list[TestPoint]
    cases: list[TestCase]
    options: CompileOptions = Field(default_factory=CompileOptions)


class CompileBundleResponse(BaseModel):
    """编译 bundle 返回"""
    ok: bool
    compiled: list[CompiledCase] = Field(default_factory=list)


# ============================================================
# 4) Execute Bundle（一键：bundle -> compile -> execute）
# ============================================================

class ExecuteBundleCompileOptions(BaseModel):
    """
    一键执行中的编译选项（与 compile_bundle 的 options 对齐）
    """
    target: str = "playwright_dsl_v1"
    strict: bool = True
    default_timeout_ms: int = 15000


class ExecuteBundleRunOptions(BaseModel):
    """
    一键执行中的运行选项
    """
    base_url: Optional[str] = None
    headless: bool = True


class ExecuteBundleCompiledCase(BaseModel):
    """
    供调试/排查用：bundle 内某条 case 的编译结果
    注意：这不是执行结果，执行结果统一用 ExecutionResponse。
    """
    case_id: str
    title: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CaseExecutionResult(BaseModel):
    """
    Bundle 中单条 Case 的执行结果。
    - execution：若进入执行阶段，返回统一 ExecutionResponse（包含 artifact_dir/evidence）
    """
    case_id: str
    title: str
    ok: bool
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    execution: ExecutionResponse | None = None


class ExecuteBundleRequest(BaseModel):
    """
    一键执行请求：
    - bundle：/generate 的输出
    - case_index：执行第几条（默认 0，冒烟用例）
    - compile_options/run：可覆盖
    """
    bundle: CaseBundle
    case_index: int = 0
    compile_options: ExecuteBundleCompileOptions = Field(default_factory=ExecuteBundleCompileOptions)
    run: ExecuteBundleRunOptions = Field(default_factory=ExecuteBundleRunOptions)


class ExecuteBundleResponse(BaseModel):
    """一键执行返回：results 内每条复用统一的 ExecutionResponse"""
    ok: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifact_dir: str | None = None
    results: list[CaseExecutionResult] = Field(default_factory=list)
