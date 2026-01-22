"""Tests for Phase 5.1.1 Budget Short-Circuit feature.

Tests verify that:
1. Budget exceeding threshold triggers short-circuit with FAIL decision
2. Budget within threshold doesn't affect original decision
3. Short-circuited runs still generate evidence.json
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from qualityfoundry.governance import GateDecision
from qualityfoundry.governance.gate import GateResult
from qualityfoundry.governance.policy_loader import PolicyConfig, CostGovernance
from qualityfoundry.services.orchestrator_service import (
    OrchestratorService,
    OrchestrationInput,
    OrchestrationState,
    GovernanceBudget,
)
from qualityfoundry.tools.contracts import ToolRequest, ToolResult, ToolMetrics


class TestEnforceBudget:
    """Tests for _enforce_budget method."""

    def test_enforce_budget_exceeds_threshold(self):
        """When elapsed > policy.timeout_s * 1000, should set decision=FAIL and short_circuit=True."""
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

        # Policy with 1 second timeout (1000ms)
        policy = PolicyConfig(cost_governance=CostGovernance(timeout_s=1))

        # Budget with 2000ms elapsed (exceeds 1000ms limit)
        budget: GovernanceBudget = {
            "elapsed_ms_total": 2000,
            "attempts_total": 1,
            "retries_used_total": 0,
            "short_circuited": False,
            "short_circuit_reason": None,
        }

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": policy,
            "budget": budget,
        }

        result = service._enforce_budget(state)

        # Should trigger short-circuit
        assert result["decision"] == GateDecision.FAIL
        assert result["budget"]["short_circuited"] is True
        assert result["budget"]["short_circuit_reason"] == "budget_elapsed_exceeded"
        assert "2000ms > 1000ms" in result["reason"]

    def test_enforce_budget_within_threshold(self):
        """When elapsed <= policy.timeout_s * 1000, should not affect state."""
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

        # Policy with 10 second timeout (10000ms)
        policy = PolicyConfig(cost_governance=CostGovernance(timeout_s=10))

        # Budget with 500ms elapsed (within 10000ms limit)
        budget: GovernanceBudget = {
            "elapsed_ms_total": 500,
            "attempts_total": 1,
            "retries_used_total": 0,
            "short_circuited": False,
            "short_circuit_reason": None,
        }

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": policy,
            "budget": budget,
        }

        result = service._enforce_budget(state)

        # Should NOT trigger short-circuit - state unchanged
        assert result is state  # Same object reference
        assert "decision" not in result  # No decision set
        assert result["budget"]["short_circuited"] is False


class TestShortCircuitEvidence:
    """Tests for evidence generation during short-circuit."""

    @pytest.mark.asyncio
    async def test_short_circuit_still_generates_evidence(self):
        """Even when short-circuited, evidence.json should be generated with governance info."""
        db = MagicMock()

        # Mock collector
        mock_evidence = MagicMock()
        mock_evidence.model_dump.return_value = {
            "run_id": "test",
            "input_nl": "run tests",
            "tool_calls": [],
        }
        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_evidence
        mock_collector.save.return_value = "/path/to/evidence.json"
        mock_collector_factory = MagicMock(return_value=mock_collector)

        # Policy with 1 second timeout (1000ms)
        mock_policy = PolicyConfig(cost_governance=CostGovernance(timeout_s=1))

        service = OrchestratorService(
            db,
            collector_factory=mock_collector_factory,
        )

        run_id = uuid4()
        input_data = OrchestrationInput(
            nl_input="run tests",
            environment_id=None,
            tool_name="run_pytest",
            tool_args={},
            timeout_s=120,
            dry_run=False,
        )

        # Create state with budget already exceeding threshold
        budget: GovernanceBudget = {
            "elapsed_ms_total": 5000,  # 5 seconds > 1 second limit
            "attempts_total": 1,
            "retries_used_total": 0,
            "short_circuited": False,
            "short_circuit_reason": None,
        }

        tool_request = ToolRequest(
            tool_name="run_pytest",
            args={},
            run_id=run_id,
            timeout_s=120,
        )
        tool_result = ToolResult.success(stdout="Tests passed")

        state: OrchestrationState = {
            "run_id": run_id,
            "input": input_data,
            "policy": mock_policy,
            "budget": budget,
            "tool_request": tool_request,
            "tool_result": tool_result,
        }

        # Step 1: enforce_budget should trigger short-circuit
        state = service._enforce_budget(state)
        assert state["decision"] == GateDecision.FAIL
        assert state["budget"]["short_circuited"] is True

        # Step 2: collect_evidence should still work and include governance info
        state = service._collect_evidence(state)

        # Evidence should be collected
        mock_collector.collect.assert_called_once()
        mock_collector.save.assert_called_once()

        # Evidence should contain governance info with short_circuit flag
        assert "governance" in state["evidence"]
        assert state["evidence"]["governance"]["short_circuited"] is True
        assert state["evidence"]["governance"]["short_circuit_reason"] == "budget_elapsed_exceeded"
