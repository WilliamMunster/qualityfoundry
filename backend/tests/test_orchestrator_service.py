"""Unit tests for OrchestratorService (Phase 1.2)."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from qualityfoundry.api.v1.routes_orchestrations import OrchestrationRequest, OrchestrationOptions
from qualityfoundry.governance.policy_loader import PolicyConfig
from qualityfoundry.services.orchestrator_service import (
    OrchestratorService,
    OrchestrationInput,
    OrchestrationState,
)
from qualityfoundry.tools.contracts import ToolRequest, ToolResult


class TestNormalizeInput:
    """Tests for _normalize_input method."""

    def test_normalize_with_options(self):
        """When options provided, use them directly."""
        db = MagicMock()
        service = OrchestratorService(db)

        req = OrchestrationRequest(
            nl_input="run tests",
            environment_id=None,
            options=OrchestrationOptions(
                tool_name="run_pytest",
                args={"test_path": "tests/unit"},
                timeout_s=60,
                dry_run=True,
            ),
        )

        result = service._normalize_input(req)

        assert isinstance(result, OrchestrationInput)
        assert result.nl_input == "run tests"
        assert result.tool_name == "run_pytest"
        assert result.tool_args == {"test_path": "tests/unit"}
        assert result.timeout_s == 60
        assert result.dry_run is True

    def test_normalize_without_options_defaults_to_pytest(self):
        """When no options, default to pytest with 'tests' path."""
        db = MagicMock()
        service = OrchestratorService(db)

        req = OrchestrationRequest(
            nl_input="run my tests please",
            environment_id=None,
            options=None,
        )

        result = service._normalize_input(req)

        assert result.tool_name == "run_pytest"
        assert result.tool_args == {"test_path": "tests"}
        assert result.timeout_s == 120
        assert result.dry_run is False

    def test_normalize_playwright_keyword(self):
        """When nl_input contains 'playwright', select playwright tool."""
        db = MagicMock()
        service = OrchestratorService(db)

        req = OrchestrationRequest(
            nl_input="run playwright e2e tests",
            environment_id=None,
            options=None,
        )

        result = service._normalize_input(req)

        assert result.tool_name == "run_playwright"
        assert result.timeout_s == 300


class TestLoadPolicy:
    """Tests for _load_policy method."""

    def test_load_policy_uses_injected_loader(self):
        """When policy_loader is injected, use it to load policy."""
        db = MagicMock()
        mock_policy = PolicyConfig(
            version="2.0",
            high_risk_keywords=["danger"],
        )
        mock_loader = MagicMock(return_value=mock_policy)

        service = OrchestratorService(db, policy_loader=mock_loader)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={"test_path": "tests"},
            timeout_s=120,
            dry_run=False,
        )

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
        }

        result = service._load_policy(state)

        mock_loader.assert_called_once()
        assert result["policy"] == mock_policy
        assert result["policy_meta"]["version"] == "2.0"

    def test_load_policy_preserves_existing_state(self):
        """_load_policy should preserve existing state keys."""
        db = MagicMock()
        mock_policy = PolicyConfig()
        mock_loader = MagicMock(return_value=mock_policy)

        service = OrchestratorService(db, policy_loader=mock_loader)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={"test_path": "tests"},
            timeout_s=120,
            dry_run=False,
        )

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
        }

        result = service._load_policy(state)

        # Original keys preserved
        assert result["run_id"] == run_id
        assert result["input"] == input_data


class TestPlanToolRequest:
    """Tests for _plan_tool_request method."""

    def test_plan_tool_request_builds_request(self):
        """_plan_tool_request should build ToolRequest from input."""
        db = MagicMock()
        service = OrchestratorService(db)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run unit tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={"test_path": "tests/unit"},
            timeout_s=60,
            dry_run=True,
        )

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": PolicyConfig(),
            "policy_meta": {"version": "1.0"},
        }

        result = service._plan_tool_request(state)

        assert "tool_request" in result
        req = result["tool_request"]
        assert isinstance(req, ToolRequest)
        assert req.tool_name == "run_pytest"
        assert req.args == {"test_path": "tests/unit"}
        assert req.run_id == run_id
        assert req.timeout_s == 60
        assert req.dry_run is True

    def test_plan_tool_request_preserves_state(self):
        """_plan_tool_request should preserve existing state."""
        db = MagicMock()
        service = OrchestratorService(db)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={},
            timeout_s=120,
            dry_run=False,
        )
        mock_policy = PolicyConfig()

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": mock_policy,
            "policy_meta": {"version": "1.0"},
        }

        result = service._plan_tool_request(state)

        # Original keys preserved
        assert result["run_id"] == run_id
        assert result["input"] == input_data
        assert result["policy"] == mock_policy


class TestExecuteTools:
    """Tests for _execute_tools method (async)."""

    @pytest.mark.asyncio
    async def test_execute_tools_calls_registry(self):
        """_execute_tools should use registry to execute tool."""
        db = MagicMock()

        # Mock registry
        mock_result = ToolResult.success(stdout="All tests passed")
        mock_registry = MagicMock()
        mock_registry.execute = AsyncMock(return_value=mock_result)

        service = OrchestratorService(db, registry=mock_registry)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={"test_path": "tests"},
            timeout_s=120,
            dry_run=False,
        )
        tool_request = ToolRequest(
            tool_name="run_pytest",
            args={"test_path": "tests"},
            run_id=run_id,
            timeout_s=120,
            dry_run=False,
        )

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": PolicyConfig(),
            "policy_meta": {"version": "1.0"},
            "tool_request": tool_request,
        }

        result = await service._execute_tools(state)

        mock_registry.execute.assert_called_once_with("run_pytest", tool_request)
        assert result["tool_result"] == mock_result

    @pytest.mark.asyncio
    async def test_execute_tools_preserves_state(self):
        """_execute_tools should preserve existing state."""
        db = MagicMock()

        mock_result = ToolResult.success()
        mock_registry = MagicMock()
        mock_registry.execute = AsyncMock(return_value=mock_result)

        service = OrchestratorService(db, registry=mock_registry)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={},
            timeout_s=120,
            dry_run=False,
        )
        tool_request = ToolRequest(
            tool_name="run_pytest",
            args={},
            run_id=run_id,
            timeout_s=120,
        )
        mock_policy = PolicyConfig()

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": mock_policy,
            "policy_meta": {"version": "1.0"},
            "tool_request": tool_request,
        }

        result = await service._execute_tools(state)

        assert result["run_id"] == run_id
        assert result["input"] == input_data
        assert result["policy"] == mock_policy
        assert result["tool_request"] == tool_request


class TestCollectEvidence:
    """Tests for _collect_evidence method."""

    def test_collect_evidence_creates_evidence(self):
        """_collect_evidence should use collector to create evidence."""
        db = MagicMock()

        # Mock collector factory
        mock_evidence = MagicMock()
        mock_evidence.model_dump.return_value = {"run_id": "test", "summary": {}}
        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_evidence
        mock_collector.save.return_value = "/path/to/evidence.json"

        mock_collector_factory = MagicMock(return_value=mock_collector)

        service = OrchestratorService(db, collector_factory=mock_collector_factory)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={"test_path": "tests"},
            timeout_s=120,
            dry_run=False,
        )
        tool_request = ToolRequest(
            tool_name="run_pytest",
            args={"test_path": "tests"},
            run_id=run_id,
            timeout_s=120,
        )
        tool_result = ToolResult.success(stdout="OK")

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": PolicyConfig(),
            "policy_meta": {"version": "1.0"},
            "tool_request": tool_request,
            "tool_result": tool_result,
        }

        result = service._collect_evidence(state)

        # Collector factory was called with correct args
        mock_collector_factory.assert_called_once()
        # Tool result was added
        mock_collector.add_tool_result.assert_called_once_with("run_pytest", tool_result)
        # Evidence collected and saved
        mock_collector.collect.assert_called_once()
        mock_collector.save.assert_called_once()
        # State updated
        assert "evidence" in result

    def test_collect_evidence_preserves_state(self):
        """_collect_evidence should preserve existing state."""
        db = MagicMock()

        mock_evidence = MagicMock()
        mock_evidence.model_dump.return_value = {}
        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_evidence
        mock_collector.save.return_value = "/path/to/evidence.json"
        mock_collector_factory = MagicMock(return_value=mock_collector)

        service = OrchestratorService(db, collector_factory=mock_collector_factory)

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={},
            timeout_s=120,
            dry_run=False,
        )
        tool_request = ToolRequest(
            tool_name="run_pytest",
            args={},
            run_id=run_id,
            timeout_s=120,
        )
        tool_result = ToolResult.success()
        mock_policy = PolicyConfig()

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": mock_policy,
            "policy_meta": {"version": "1.0"},
            "tool_request": tool_request,
            "tool_result": tool_result,
        }

        result = service._collect_evidence(state)

        assert result["run_id"] == run_id
        assert result["input"] == input_data
        assert result["tool_result"] == tool_result


class TestGateAndHitl:
    """Tests for _gate_and_hitl method."""

    def test_gate_and_hitl_pass_decision(self):
        """_gate_and_hitl should set decision=PASS when gate passes."""
        from qualityfoundry.governance import GateDecision
        from qualityfoundry.governance.gate import GateResult

        db = MagicMock()

        # Mock gate evaluator that returns PASS
        mock_gate_result = GateResult(
            decision=GateDecision.PASS,
            reason="All tests passed",
        )
        mock_gate_evaluator = MagicMock(return_value=mock_gate_result)

        service = OrchestratorService(db, gate_evaluator=mock_gate_evaluator)
        service._approval_service = MagicMock()

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={},
            timeout_s=120,
            dry_run=False,
        )

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": PolicyConfig(),
            "policy_meta": {"version": "1.0"},
            "tool_request": ToolRequest(tool_name="run_pytest", args={}, run_id=run_id, timeout_s=120),
            "tool_result": ToolResult.success(),
            "evidence": {"run_id": str(run_id), "input_nl": "run tests", "tool_calls": []},
        }

        result = service._gate_and_hitl(state)

        assert result["decision"] == GateDecision.PASS
        assert result["reason"] == "All tests passed"
        assert result["approval_id"] is None

    def test_gate_and_hitl_fail_decision(self):
        """_gate_and_hitl should set decision=FAIL when gate fails."""
        from qualityfoundry.governance import GateDecision
        from qualityfoundry.governance.gate import GateResult

        db = MagicMock()

        mock_gate_result = GateResult(
            decision=GateDecision.FAIL,
            reason="2 tests failed",
        )
        mock_gate_evaluator = MagicMock(return_value=mock_gate_result)

        service = OrchestratorService(db, gate_evaluator=mock_gate_evaluator)
        service._approval_service = MagicMock()

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={},
            timeout_s=120,
            dry_run=False,
        )

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": PolicyConfig(),
            "policy_meta": {"version": "1.0"},
            "tool_request": ToolRequest(tool_name="run_pytest", args={}, run_id=run_id, timeout_s=120),
            "tool_result": ToolResult.failed(error_message="Tests failed"),
            "evidence": {"run_id": str(run_id), "input_nl": "run tests", "tool_calls": []},
        }

        result = service._gate_and_hitl(state)

        assert result["decision"] == GateDecision.FAIL
        assert result["reason"] == "2 tests failed"

    def test_gate_and_hitl_need_hitl_creates_approval(self):
        """_gate_and_hitl should create approval when NEED_HITL."""
        from qualityfoundry.governance import GateDecision
        from qualityfoundry.governance.gate import GateResult

        db = MagicMock()

        approval_id = uuid4()
        mock_gate_result = GateResult(
            decision=GateDecision.NEED_HITL,
            reason="High-risk keyword detected: production",
            approval_id=approval_id,
        )
        mock_gate_evaluator = MagicMock(return_value=mock_gate_result)

        service = OrchestratorService(db, gate_evaluator=mock_gate_evaluator)
        service._approval_service = MagicMock()
        mock_approval = MagicMock()
        mock_approval.id = approval_id
        service._approval_service.create_approval.return_value = mock_approval

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="deploy to production",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={},
            timeout_s=120,
            dry_run=False,
        )

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": PolicyConfig(),
            "policy_meta": {"version": "1.0"},
            "tool_request": ToolRequest(tool_name="run_pytest", args={}, run_id=run_id, timeout_s=120),
            "tool_result": ToolResult.success(),
            "evidence": {"run_id": str(run_id), "input_nl": "deploy to production", "tool_calls": []},
        }

        result = service._gate_and_hitl(state)

        assert result["decision"] == GateDecision.NEED_HITL
        assert result["approval_id"] == approval_id


class TestRun:
    """Tests for run method (complete pipeline)."""

    @pytest.mark.asyncio
    async def test_run_executes_full_pipeline(self):
        """run should execute the complete orchestration pipeline."""
        from qualityfoundry.governance import GateDecision
        from qualityfoundry.governance.gate import GateResult
        from qualityfoundry.services.orchestrator_service import OrchestrationResult

        db = MagicMock()

        # Mock all dependencies
        mock_policy = PolicyConfig()
        mock_policy_loader = MagicMock(return_value=mock_policy)

        mock_tool_result = ToolResult.success(stdout="All tests passed")
        mock_registry = MagicMock()
        mock_registry.execute = AsyncMock(return_value=mock_tool_result)

        mock_evidence = MagicMock()
        mock_evidence.model_dump.return_value = {"run_id": "test", "input_nl": "run tests", "tool_calls": []}
        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_evidence
        mock_collector.save.return_value = "/path/to/evidence.json"
        mock_collector_factory = MagicMock(return_value=mock_collector)

        mock_gate_result = GateResult(
            decision=GateDecision.PASS,
            reason="All tests passed",
        )
        mock_gate_evaluator = MagicMock(return_value=mock_gate_result)

        service = OrchestratorService(
            db,
            registry=mock_registry,
            policy_loader=mock_policy_loader,
            collector_factory=mock_collector_factory,
            gate_evaluator=mock_gate_evaluator,
        )
        service._approval_service = MagicMock()

        req = OrchestrationRequest(
            nl_input="run tests",
            environment_id=None,
            options=None,
        )

        result = await service.run(req)

        # Verify result type and fields
        assert isinstance(result, OrchestrationResult)
        assert result.decision == GateDecision.PASS
        assert result.reason == "All tests passed"

        # Verify pipeline was executed
        mock_policy_loader.assert_called_once()
        mock_registry.execute.assert_called_once()
        mock_collector.add_tool_result.assert_called_once()
        mock_gate_evaluator.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_returns_result_with_approval_id(self):
        """run should include approval_id when NEED_HITL."""
        from qualityfoundry.governance import GateDecision
        from qualityfoundry.governance.gate import GateResult

        db = MagicMock()
        approval_id = uuid4()

        mock_policy = PolicyConfig()
        mock_policy_loader = MagicMock(return_value=mock_policy)

        mock_tool_result = ToolResult.success()
        mock_registry = MagicMock()
        mock_registry.execute = AsyncMock(return_value=mock_tool_result)

        mock_evidence = MagicMock()
        mock_evidence.model_dump.return_value = {"run_id": "test", "input_nl": "deploy prod", "tool_calls": []}
        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_evidence
        mock_collector.save.return_value = "/path/to/evidence.json"
        mock_collector_factory = MagicMock(return_value=mock_collector)

        mock_gate_result = GateResult(
            decision=GateDecision.NEED_HITL,
            reason="High-risk keyword: production",
            approval_id=approval_id,
        )
        mock_gate_evaluator = MagicMock(return_value=mock_gate_result)

        service = OrchestratorService(
            db,
            registry=mock_registry,
            policy_loader=mock_policy_loader,
            collector_factory=mock_collector_factory,
            gate_evaluator=mock_gate_evaluator,
        )
        service._approval_service = MagicMock()
        mock_approval = MagicMock()
        mock_approval.id = approval_id
        service._approval_service.create_approval.return_value = mock_approval

        req = OrchestrationRequest(
            nl_input="deploy to production",
            environment_id=None,
            options=None,
        )

        result = await service.run(req)

        assert result.decision == GateDecision.NEED_HITL
        assert result.approval_id == approval_id


class TestLangGraphState:
    """Tests for LangGraph state compatibility."""

    def test_langgraph_state_has_required_annotations(self):
        """LangGraphState should have all required field annotations for LangGraph."""
        from qualityfoundry.services.orchestrator_service import LangGraphState
        from typing import get_type_hints

        hints = get_type_hints(LangGraphState)

        # Required fields
        assert "run_id" in hints
        assert "input" in hints
        assert "policy" in hints
        assert "tool_request" in hints
        assert "tool_result" in hints
        assert "evidence" in hints
        assert "decision" in hints
        assert "reason" in hints


class TestRunWithGraph:
    """Tests for run_with_graph method."""

    @pytest.mark.asyncio
    async def test_run_with_graph_returns_same_result_as_run(self):
        """run_with_graph should produce identical results to run."""
        from qualityfoundry.governance import GateDecision
        from qualityfoundry.governance.gate import GateResult
        from qualityfoundry.services.orchestrator_service import OrchestrationResult

        db = MagicMock()

        # Mock all dependencies (same as TestRun)
        mock_policy = PolicyConfig()
        mock_policy_loader = MagicMock(return_value=mock_policy)

        mock_tool_result = ToolResult.success(stdout="All tests passed")
        mock_registry = MagicMock()
        mock_registry.execute = AsyncMock(return_value=mock_tool_result)

        mock_evidence = MagicMock()
        mock_evidence.model_dump.return_value = {"run_id": "test", "input_nl": "run tests", "tool_calls": []}
        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_evidence
        mock_collector.save.return_value = "/path/to/evidence.json"
        mock_collector_factory = MagicMock(return_value=mock_collector)

        mock_gate_result = GateResult(
            decision=GateDecision.PASS,
            reason="All tests passed",
        )
        mock_gate_evaluator = MagicMock(return_value=mock_gate_result)

        service = OrchestratorService(
            db,
            registry=mock_registry,
            policy_loader=mock_policy_loader,
            collector_factory=mock_collector_factory,
            gate_evaluator=mock_gate_evaluator,
        )
        service._approval_service = MagicMock()

        req = OrchestrationRequest(
            nl_input="run tests",
            environment_id=None,
            options=None,
        )

        # Run both methods
        result_legacy = await service.run(req)

        # Reset mocks for second run
        mock_policy_loader.reset_mock()
        mock_registry.execute.reset_mock()
        mock_collector.add_tool_result.reset_mock()
        mock_gate_evaluator.reset_mock()

        result_graph = await service.run_with_graph(req)

        # Results should be equivalent (except run_id which is generated fresh)
        assert result_graph.decision == result_legacy.decision
        assert result_graph.reason == result_legacy.reason


class TestGraphBuilder:
    """Tests for LangGraph graph construction."""

    def test_build_graph_returns_compiled_graph(self):
        """build_orchestration_graph should return a compiled StateGraph."""
        from langgraph.graph.state import CompiledStateGraph
        from qualityfoundry.services.orchestrator_service import build_orchestration_graph, OrchestratorService
        from unittest.mock import MagicMock

        db = MagicMock()
        service = OrchestratorService(db)

        graph = build_orchestration_graph(service)

        assert isinstance(graph, CompiledStateGraph)

    def test_build_graph_has_expected_nodes(self):
        """build_orchestration_graph should include all 5 node steps."""
        from qualityfoundry.services.orchestrator_service import build_orchestration_graph, OrchestratorService
        from unittest.mock import MagicMock

        db = MagicMock()
        service = OrchestratorService(db)

        graph = build_orchestration_graph(service)

        # Check nodes exist (LangGraph exposes nodes via .nodes)
        node_names = set(graph.nodes.keys())
        expected_nodes = {"load_policy", "plan_tool_request", "execute_tools", "collect_evidence", "gate_and_hitl"}

        assert expected_nodes.issubset(node_names)
