from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class CompileOptions(BaseModel):
    target: Literal["playwright_dsl_v1"] = "playwright_dsl_v1"
    strict: bool = True
    default_timeout_ms: int = 15000


class BundleRequirement(BaseModel):
    title: str
    text: str
    domain: str | None = None


class BundleModule(BaseModel):
    id: str
    name: str
    description: str | None = None


class BundleObjective(BaseModel):
    id: str
    module_id: str
    name: str
    description: str | None = None


class BundleTestPoint(BaseModel):
    id: str
    objective_id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class BundleStep(BaseModel):
    step: str
    expected: str | None = None


class BundleCase(BaseModel):
    id: str
    objective_id: str
    title: str
    preconditions: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    priority: str = "P1"
    tags: list[str] = Field(default_factory=list)
    steps: list[BundleStep]


class CompileBundleRequest(BaseModel):
    requirement: BundleRequirement
    modules: list[BundleModule]
    objectives: list[BundleObjective]
    test_points: list[BundleTestPoint]
    cases: list[BundleCase]
    options: CompileOptions = Field(default_factory=CompileOptions)


class CompiledCase(BaseModel):
    case_id: str
    title: str
    actions: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)


class CompileBundleResponse(BaseModel):
    ok: bool = True
    compiled: list[CompiledCase]
