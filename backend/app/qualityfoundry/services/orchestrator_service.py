"""QualityFoundry - Orchestrator Service (L2 Orchestration Layer)

Phase 1.2: Service abstraction with LangGraph-ready node boundaries.

Design decisions:
- Dependency injection: DB required, registry/collector/policy optional (testable)
- Return type: OrchestrationResult (domain object, no HTTP concepts)
- Input: OrchestrationRequest (API DTO) + internal normalization
- Node methods: _load_policy, _plan_tool_request, _execute_tools, _collect_evidence, _gate_and_hitl
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict
from uuid import UUID

from qualityfoundry.governance import GateDecision
from qualityfoundry.governance.policy_loader import PolicyConfig
from qualityfoundry.tools.contracts import ToolRequest, ToolResult


@dataclass(frozen=True)
class OrchestrationInput:
    """Internal normalized input (decoupled from API DTO)."""
    nl_input: str
    environment_id: UUID | None
    tool_name: str
    tool_args: dict[str, Any]
    timeout_s: int
    dry_run: bool


@dataclass(frozen=True)
class OrchestrationResult:
    """Service return type (domain object, no HTTP concepts)."""
    run_id: UUID
    decision: GateDecision
    reason: str
    evidence: dict[str, Any]
    execution_id: UUID | None = None
    approval_id: UUID | None = None
    report_path: Path | None = None


class OrchestrationState(TypedDict, total=False):
    """Mutable state passed through node methods (LangGraph-ready)."""
    run_id: UUID
    input: OrchestrationInput
    policy: PolicyConfig
    policy_meta: dict[str, Any]
    tool_request: ToolRequest
    tool_result: ToolResult
    evidence: dict[str, Any]
    decision: GateDecision
    reason: str
    approval_id: UUID | None
    report_path: Path | None
