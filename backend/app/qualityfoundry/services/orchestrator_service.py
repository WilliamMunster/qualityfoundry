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
from typing import Any, Callable, TypedDict
from uuid import UUID

from sqlalchemy.orm import Session

from qualityfoundry.api.v1.routes_orchestrations import OrchestrationRequest
from qualityfoundry.governance import GateDecision
from qualityfoundry.governance.policy_loader import get_policy, PolicyConfig
from qualityfoundry.governance.tracing.collector import TraceCollector
from qualityfoundry.services.approval_service import ApprovalService
from qualityfoundry.tools.contracts import ToolRequest, ToolResult
from qualityfoundry.tools.registry import get_registry, ToolRegistry


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


# Type alias for collector factory (testability)
CollectorFactory = Callable[[UUID, str, dict[str, Any]], TraceCollector]


def _default_collector_factory(run_id: UUID, input_nl: str, environment: dict[str, Any]) -> TraceCollector:
    """Default factory creates real TraceCollector."""
    return TraceCollector(run_id=str(run_id), input_nl=input_nl, environment=environment)


class OrchestratorService:
    """Orchestration service with LangGraph-ready node boundaries.

    Dependency injection:
    - db: Required (for ApprovalService)
    - registry: Optional (default: global singleton)
    - collector_factory: Optional (default: creates real TraceCollector)
    - policy_loader: Optional (default: loads from file)
    """

    def __init__(
        self,
        db: Session,
        *,
        registry: ToolRegistry | None = None,
        collector_factory: CollectorFactory | None = None,
        policy_loader: Callable[[], PolicyConfig] | None = None,
    ):
        self._db = db
        self._registry = registry
        self._collector_factory = collector_factory or _default_collector_factory
        self._policy_loader = policy_loader or get_policy
        self._approval_service = ApprovalService(db)

    @property
    def registry(self) -> ToolRegistry:
        """Lazy registry access (allows late binding for tests)."""
        return self._registry or get_registry()

    async def run(self, req: OrchestrationRequest) -> OrchestrationResult:
        """Execute orchestration pipeline.

        Pipeline: normalize → load_policy → plan → execute → collect → gate
        """
        raise NotImplementedError("Task 7 will implement this")

    def _normalize_input(self, req: OrchestrationRequest) -> OrchestrationInput:
        """Convert API DTO to internal normalized input.

        Priority:
        1. If options provided, use them directly (deterministic mode)
        2. Otherwise, use simple heuristic based on nl_input keywords
        """
        if req.options:
            return OrchestrationInput(
                nl_input=req.nl_input,
                environment_id=req.environment_id,
                tool_name=req.options.tool_name,
                tool_args=req.options.args,
                timeout_s=req.options.timeout_s,
                dry_run=req.options.dry_run,
            )

        # Simple heuristic: detect playwright/browser/e2e keywords
        nl_lower = req.nl_input.lower()
        if "playwright" in nl_lower or "browser" in nl_lower or "e2e" in nl_lower:
            return OrchestrationInput(
                nl_input=req.nl_input,
                environment_id=req.environment_id,
                tool_name="run_playwright",
                tool_args={},
                timeout_s=300,
                dry_run=False,
            )

        # Default: pytest with 'tests' path
        return OrchestrationInput(
            nl_input=req.nl_input,
            environment_id=req.environment_id,
            tool_name="run_pytest",
            tool_args={"test_path": "tests"},
            timeout_s=120,
            dry_run=False,
        )

    def _load_policy(self, state: OrchestrationState) -> OrchestrationState:
        """Node 1: Load policy configuration."""
        raise NotImplementedError("Task 4 will implement this")

    def _plan_tool_request(self, state: OrchestrationState) -> OrchestrationState:
        """Node 2: Build tool request from input."""
        raise NotImplementedError("Task 4 will implement this")

    async def _execute_tools(self, state: OrchestrationState) -> OrchestrationState:
        """Node 3: Execute tool and collect result."""
        raise NotImplementedError("Task 5 will implement this")

    def _collect_evidence(self, state: OrchestrationState) -> OrchestrationState:
        """Node 4: Collect evidence and save to disk."""
        raise NotImplementedError("Task 5 will implement this")

    def _gate_and_hitl(self, state: OrchestrationState) -> OrchestrationState:
        """Node 5: Evaluate gate and create approval if needed."""
        raise NotImplementedError("Task 6 will implement this")
