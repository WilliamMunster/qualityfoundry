from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


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
