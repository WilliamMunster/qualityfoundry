"""Unit tests for OrchestratorService (Phase 1.2)."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from qualityfoundry.api.v1.routes_orchestrations import OrchestrationRequest, OrchestrationOptions
from qualityfoundry.services.orchestrator_service import (
    OrchestratorService,
    OrchestrationInput,
)


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
