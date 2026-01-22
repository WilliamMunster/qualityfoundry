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
from qualityfoundry.governance import GateDecision, evaluate_gate_with_hitl
from qualityfoundry.governance.gate import GateResult
from qualityfoundry.governance.tracing.collector import Evidence
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
        gate_evaluator: Callable[[Evidence], GateResult] | None = None,
    ):
        self._db = db
        self._registry = registry
        self._collector_factory = collector_factory or _default_collector_factory
        self._policy_loader = policy_loader or get_policy
        self._gate_evaluator = gate_evaluator or evaluate_gate_with_hitl
        self._approval_service = ApprovalService(db)

    @property
    def registry(self) -> ToolRegistry:
        """Lazy registry access (allows late binding for tests)."""
        return self._registry or get_registry()

    async def run(self, req: OrchestrationRequest) -> OrchestrationResult:
        """Execute orchestration pipeline.

        Pipeline: normalize → load_policy → plan → execute → collect → gate

        Returns:
            OrchestrationResult with decision, reason, evidence, and optional approval_id
        """
        from uuid import uuid4

        # Generate run_id
        run_id = uuid4()

        # Step 1: Normalize input
        normalized_input = self._normalize_input(req)

        # Initialize state
        state: OrchestrationState = {
            "run_id": run_id,
            "input": normalized_input,
        }

        # Step 2: Load policy
        state = self._load_policy(state)

        # Step 3: Plan tool request
        state = self._plan_tool_request(state)

        # Step 4: Execute tools
        state = await self._execute_tools(state)

        # Step 5: Collect evidence
        state = self._collect_evidence(state)

        # Step 6: Gate and HITL
        state = self._gate_and_hitl(state)

        # Build result
        return OrchestrationResult(
            run_id=run_id,
            decision=state["decision"],
            reason=state["reason"],
            evidence=state["evidence"],
            approval_id=state.get("approval_id"),
            report_path=state.get("report_path"),
        )

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
        """Node 1: Load policy configuration.

        Uses injected policy_loader or default get_policy().
        Adds 'policy' and 'policy_meta' to state.
        """
        policy = self._policy_loader()

        # Return new state with policy added (preserve existing keys)
        return {
            **state,
            "policy": policy,
            "policy_meta": {
                "version": policy.version,
                "high_risk_keywords_count": len(policy.high_risk_keywords),
                "high_risk_patterns_count": len(policy.high_risk_patterns),
            },
        }

    def _plan_tool_request(self, state: OrchestrationState) -> OrchestrationState:
        """Node 2: Build tool request from input.

        Creates ToolRequest from OrchestrationInput.
        Adds 'tool_request' to state.
        """
        input_data = state["input"]

        tool_request = ToolRequest(
            tool_name=input_data.tool_name,
            args=input_data.tool_args,
            run_id=state["run_id"],
            timeout_s=input_data.timeout_s,
            dry_run=input_data.dry_run,
        )

        return {
            **state,
            "tool_request": tool_request,
        }

    async def _execute_tools(self, state: OrchestrationState) -> OrchestrationState:
        """Node 3: Execute tool and collect result.

        Uses registry to execute the tool request.
        Adds 'tool_result' to state.
        """
        tool_request = state["tool_request"]

        tool_result = await self.registry.execute(
            tool_request.tool_name,
            tool_request,
        )

        return {
            **state,
            "tool_result": tool_result,
        }

    def _collect_evidence(self, state: OrchestrationState) -> OrchestrationState:
        """Node 4: Collect evidence and save to disk.

        Uses collector_factory to create TraceCollector.
        Adds 'evidence' and 'report_path' to state.
        """
        run_id = state["run_id"]
        input_data = state["input"]
        tool_request = state["tool_request"]
        tool_result = state["tool_result"]

        # Create collector with environment info
        environment = {
            "environment_id": str(input_data.environment_id) if input_data.environment_id else None,
        }
        collector = self._collector_factory(run_id, input_data.nl_input, environment)

        # Add tool result
        collector.add_tool_result(tool_request.tool_name, tool_result)

        # Collect and save evidence
        evidence = collector.collect()
        report_path = collector.save(evidence)

        return {
            **state,
            "evidence": evidence.model_dump(),
            "report_path": report_path,
        }

    def _gate_and_hitl(self, state: OrchestrationState) -> OrchestrationState:
        """Node 5: Evaluate gate and create approval if needed.

        Uses gate_evaluator to evaluate evidence.
        Adds 'decision', 'reason', and 'approval_id' to state.
        """
        evidence_dict = state["evidence"]

        # Reconstruct Evidence object from dict for gate evaluation
        evidence = Evidence.model_validate(evidence_dict)

        # Evaluate gate
        gate_result = self._gate_evaluator(evidence)

        return {
            **state,
            "decision": gate_result.decision,
            "reason": gate_result.reason,
            "approval_id": gate_result.approval_id,
        }
