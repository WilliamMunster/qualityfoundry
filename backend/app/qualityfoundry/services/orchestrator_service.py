"""QualityFoundry - Orchestrator Service (L2 Orchestration Layer)

Phase 1.2: Service abstraction with LangGraph-ready node boundaries.

Design decisions:
- Dependency injection: DB required, registry/collector/policy optional (testable)
- Return type: OrchestrationResult (domain object, no HTTP concepts)
- Input: OrchestrationRequest (API DTO) + internal normalization
- Node methods: _load_policy, _plan_tool_request, _execute_tools, _collect_evidence, _gate_and_hitl
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from operator import add
from typing import Annotated, Any, Callable, Protocol, TypedDict
from uuid import UUID

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from qualityfoundry.governance import GateDecision, evaluate_gate
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


class GovernanceBudget(TypedDict, total=False):
    """Cost governance budget tracking (Phase 5.1).

    Tracks cumulative resource usage across all tool executions in a run.
    Used for short-circuit decisions when budget is exceeded.
    """
    elapsed_ms_total: int
    attempts_total: int
    retries_used_total: int
    short_circuited: bool
    short_circuit_reason: str | None


class LangGraphState(TypedDict, total=False):
    """State for LangGraph workflow.

    This replaces OrchestrationState for LangGraph compatibility.
    All fields are optional (total=False) to allow incremental building.
    """
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
    # For future: message history accumulation
    messages: Annotated[list[str], add]
    # Cost governance (Phase 5.1)
    budget: GovernanceBudget


# Type alias for collector factory (testability)
CollectorFactory = Callable[[UUID, str, dict[str, Any]], TraceCollector]


def _default_collector_factory(run_id: UUID, input_nl: str, environment: dict[str, Any]) -> TraceCollector:
    """Default factory creates real TraceCollector."""
    return TraceCollector(run_id=str(run_id), input_nl=input_nl, environment=environment)


class OrchestrationRequestProtocol(Protocol):
    """Protocol for orchestration request (avoids circular import)."""
    nl_input: str
    environment_id: UUID | None
    options: Any  # OrchestrationOptions or None


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
        gate_evaluator: Callable[[Evidence, PolicyConfig | None], GateResult] | None = None,
    ):
        self._db = db
        self._registry = registry
        self._collector_factory = collector_factory or _default_collector_factory
        self._policy_loader = policy_loader or get_policy
        self._gate_evaluator = gate_evaluator or evaluate_gate
        self._approval_service = ApprovalService(db)

    @property
    def registry(self) -> ToolRegistry:
        """Lazy registry access (allows late binding for tests)."""
        return self._registry or get_registry()

    async def run(self, req: OrchestrationRequestProtocol) -> OrchestrationResult:
        """Execute orchestration pipeline using LangGraph.

        Pipeline: normalize → load_policy → plan → execute → collect → gate

        This method now uses LangGraph internally for execution,
        enabling future dynamic routing and conditional branching.

        Returns:
            OrchestrationResult with decision, reason, evidence, and optional approval_id
        """
        # Delegate to graph-based implementation
        return await self.run_with_graph(req)

    async def run_with_graph(self, req: OrchestrationRequestProtocol) -> OrchestrationResult:
        """Execute orchestration using LangGraph state machine.

        This is the LangGraph-powered version of run().
        Behavior should be identical to run() but uses StateGraph for execution.

        Returns:
            OrchestrationResult with decision, reason, evidence, and optional approval_id
        """
        from uuid import uuid4

        # Generate run_id
        run_id = uuid4()

        # Normalize input
        normalized_input = self._normalize_input(req)

        # Build initial state
        initial_state: LangGraphState = {
            "run_id": run_id,
            "input": normalized_input,
            "messages": [],
        }

        # Build and run graph
        graph = build_orchestration_graph(self)

        # LangGraph invoke - handles async nodes automatically
        final_state = await graph.ainvoke(initial_state)

        # Build result from final state
        return OrchestrationResult(
            run_id=run_id,
            decision=final_state["decision"],
            reason=final_state["reason"],
            evidence=final_state["evidence"],
            approval_id=final_state.get("approval_id"),
            report_path=final_state.get("report_path"),
        )

    def _normalize_input(self, req: OrchestrationRequestProtocol) -> OrchestrationInput:
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

        Uses registry to execute the tool request with governance.
        Adds 'tool_result' and updates 'budget' in state.
        """
        from datetime import datetime, timezone
        from qualityfoundry.tools.contracts import ToolStatus, ToolMetrics
        from qualityfoundry.tools.registry import ToolNotFoundError
        from qualityfoundry.tools.base import execute_with_governance

        tool_request = state["tool_request"]

        # Get policy governance limits
        policy = state.get("policy")
        if policy and policy.cost_governance:
            # Apply policy limits to request
            tool_request = ToolRequest(
                tool_name=tool_request.tool_name,
                args=tool_request.args,
                run_id=tool_request.run_id,
                timeout_s=min(tool_request.timeout_s, policy.cost_governance.timeout_s),
                max_retries=policy.cost_governance.max_retries,
                dry_run=tool_request.dry_run,
                metadata=tool_request.metadata,
            )

        try:
            # Execute with governance (timeout + retry enforcement)
            tool_func = lambda req: self.registry.execute(req.tool_name, req)
            tool_result = await execute_with_governance(tool_func, tool_request)
        except ToolNotFoundError:
            now = datetime.now(timezone.utc)
            tool_result = ToolResult(
                status=ToolStatus.FAILED,
                stdout=None,
                stderr=f"Tool not found: {tool_request.tool_name}",
                error_message=f"Tool not found: {tool_request.tool_name}",
                started_at=now,
                ended_at=now,
                metrics=ToolMetrics(attempts=1, retries_used=0),
            )

        # Update budget with governance metrics
        prev_budget = state.get("budget", {})
        new_budget: GovernanceBudget = {
            "elapsed_ms_total": prev_budget.get("elapsed_ms_total", 0) + tool_result.metrics.duration_ms,
            "attempts_total": prev_budget.get("attempts_total", 0) + tool_result.metrics.attempts,
            "retries_used_total": prev_budget.get("retries_used_total", 0) + tool_result.metrics.retries_used,
            "short_circuited": False,
            "short_circuit_reason": None,
        }

        return {
            **state,
            "tool_result": tool_result,
            "budget": new_budget,
        }

    def _collect_evidence(self, state: OrchestrationState) -> OrchestrationState:
        """Node 4: Collect evidence and save to disk.

        Uses collector_factory to create TraceCollector.
        Adds 'evidence' and 'report_path' to state.
        Includes governance budget in evidence (Phase 5.1).
        """
        run_id = state["run_id"]
        input_data = state["input"]
        tool_request = state["tool_request"]
        tool_result = state["tool_result"]
        budget = state.get("budget", {})
        policy = state.get("policy")

        # Create collector with environment info
        environment = {
            "environment_id": str(input_data.environment_id) if input_data.environment_id else None,
        }
        collector = self._collector_factory(run_id, input_data.nl_input, environment)

        # Add tool result
        collector.add_tool_result(tool_request.tool_name, tool_result)

        # Collect and save evidence
        evidence = collector.collect()

        # Add governance info to evidence dict (Phase 5.1)
        evidence_dict = evidence.model_dump()
        evidence_dict["governance"] = {
            "budget": {
                "elapsed_ms_total": budget.get("elapsed_ms_total", 0),
                "attempts_total": budget.get("attempts_total", 0),
                "retries_used_total": budget.get("retries_used_total", 0),
            },
            "policy_limits": {
                "timeout_s": policy.cost_governance.timeout_s if policy else None,
                "max_retries": policy.cost_governance.max_retries if policy else None,
            },
            "short_circuited": budget.get("short_circuited", False),
            "short_circuit_reason": budget.get("short_circuit_reason"),
        }

        report_path = collector.save(evidence)

        return {
            **state,
            "evidence": evidence_dict,
            "report_path": report_path,
        }

    def _gate_and_hitl(self, state: OrchestrationState) -> OrchestrationState:
        """Node 5: Evaluate gate and create approval if needed.

        Uses gate_evaluator to evaluate evidence.
        Adds 'decision', 'reason', and 'approval_id' to state.
        """
        evidence_dict = state["evidence"]
        policy = state.get("policy")

        # Reconstruct Evidence object from dict for gate evaluation
        evidence = Evidence.model_validate(evidence_dict)

        # Evaluate gate
        gate_result = self._gate_evaluator(evidence, policy)

        # Create approval if NEED_HITL
        approval_id = None
        if gate_result.decision == GateDecision.NEED_HITL:
            try:
                approval = self._approval_service.create_approval(
                    entity_type="orchestration",
                    entity_id=state["run_id"],
                    reviewer=None,
                )
                approval_id = approval.id
            except Exception:
                # Approval creation failure doesn't block main flow
                pass

        return {
            **state,
            "decision": gate_result.decision,
            "reason": gate_result.reason,
            "approval_id": approval_id,
        }


def build_orchestration_graph(service: OrchestratorService) -> CompiledStateGraph:
    """Build LangGraph state machine for orchestration.

    Nodes:
    1. load_policy: Load policy configuration
    2. plan_tool_request: Build tool request from input
    3. execute_tools: Execute tool and get result
    4. collect_evidence: Collect and save evidence
    5. gate_and_hitl: Evaluate gate and create approval if needed

    Args:
        service: OrchestratorService instance with injected dependencies

    Returns:
        Compiled StateGraph ready for invocation

    Raises:
        ValueError: If service is None
    """
    if service is None:
        raise ValueError("service parameter is required")

    # Create graph with our state type
    graph = StateGraph(LangGraphState)

    # Add nodes - wrap service methods
    graph.add_node("load_policy", service._load_policy)
    graph.add_node("plan_tool_request", service._plan_tool_request)
    graph.add_node("execute_tools", service._execute_tools)
    graph.add_node("collect_evidence", service._collect_evidence)
    graph.add_node("gate_and_hitl", service._gate_and_hitl)

    # Define edges (linear flow for now, can add conditional routing later)
    graph.set_entry_point("load_policy")
    graph.add_edge("load_policy", "plan_tool_request")
    graph.add_edge("plan_tool_request", "execute_tools")
    graph.add_edge("execute_tools", "collect_evidence")
    graph.add_edge("collect_evidence", "gate_and_hitl")
    graph.add_edge("gate_and_hitl", END)

    # Compile and return
    return graph.compile()
