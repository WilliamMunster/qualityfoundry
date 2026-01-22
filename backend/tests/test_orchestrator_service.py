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
from qualityfoundry.tools.contracts import ToolRequest


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

