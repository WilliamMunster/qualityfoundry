"""Tests for Cost Governance - Orchestrator Layer (Phase 5.1 PR-2)

验证编排层的成本治理：
- LangGraphState 包含 GovernanceBudget
- _execute_tools 累计 budget
- evidence.json 包含 governance 字段
"""

from typing import get_type_hints
from uuid import uuid4

import pytest

from qualityfoundry.services.orchestrator_service import (
    GovernanceBudget,
    LangGraphState,
)


class TestGovernanceBudgetType:
    """GovernanceBudget 类型测试"""

    def test_governance_budget_has_required_fields(self):
        """验证 GovernanceBudget 包含所有必要字段"""
        hints = get_type_hints(GovernanceBudget)

        required_fields = [
            "elapsed_ms_total",
            "attempts_total",
            "retries_used_total",
            "short_circuited",
            "short_circuit_reason",
        ]
        for field in required_fields:
            assert field in hints, f"Missing field: {field}"

    def test_governance_budget_can_be_instantiated(self):
        """验证 GovernanceBudget 可以实例化"""
        budget: GovernanceBudget = {
            "elapsed_ms_total": 1000,
            "attempts_total": 3,
            "retries_used_total": 2,
            "short_circuited": False,
            "short_circuit_reason": None,
        }
        assert budget["elapsed_ms_total"] == 1000
        assert budget["attempts_total"] == 3


class TestLangGraphStateWithBudget:
    """LangGraphState 包含 budget 字段测试"""

    def test_langgraph_state_has_budget_field(self):
        """验证 LangGraphState 包含 budget 字段"""
        hints = get_type_hints(LangGraphState)
        assert "budget" in hints

    def test_langgraph_state_budget_is_governance_budget(self):
        """验证 budget 字段类型正确"""
        hints = get_type_hints(LangGraphState)
        assert hints["budget"] == GovernanceBudget


class TestExecuteToolsWithGovernance:
    """_execute_tools 集成 governance 测试"""

    @pytest.mark.asyncio
    async def test_execute_tools_populates_budget(self, setup_database):
        """验证 _execute_tools 填充 budget"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from qualityfoundry.services.orchestrator_service import (
            OrchestratorService,
            OrchestrationInput,
        )
        from qualityfoundry.governance.policy_loader import PolicyConfig
        from qualityfoundry.tools.contracts import ToolRequest

        # Create in-memory DB session
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        db = Session()

        service = OrchestratorService(db=db)
        run_id = uuid4()

        # Create minimal state
        state = {
            "run_id": run_id,
            "input": OrchestrationInput(
                nl_input="test",
                environment_id=None,
                tool_name="nonexistent_tool",  # Will fail but test budget tracking
                tool_args={},
                timeout_s=10,
                dry_run=False,
            ),
            "policy": PolicyConfig(),
            "tool_request": ToolRequest(
                tool_name="nonexistent_tool",
                args={},
                run_id=run_id,
                timeout_s=10,
            ),
        }

        result_state = await service._execute_tools(state)

        # Verify budget is populated
        assert "budget" in result_state
        budget = result_state["budget"]
        assert "elapsed_ms_total" in budget
        assert "attempts_total" in budget
        assert "retries_used_total" in budget
        assert budget["attempts_total"] >= 1

        db.close()


class TestEvidenceGovernanceField:
    """Evidence 包含 governance 字段测试"""

    def test_collect_evidence_includes_governance(self, setup_database):
        """验证 _collect_evidence 在 evidence 中包含 governance"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from qualityfoundry.services.orchestrator_service import (
            OrchestratorService,
            OrchestrationInput,
        )
        from qualityfoundry.governance.policy_loader import PolicyConfig
        from qualityfoundry.tools.contracts import ToolRequest, ToolResult, ToolStatus, ToolMetrics

        # Create in-memory DB session
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        db = Session()

        service = OrchestratorService(db=db)
        run_id = uuid4()

        # Create state with budget
        state = {
            "run_id": run_id,
            "input": OrchestrationInput(
                nl_input="test governance evidence",
                environment_id=None,
                tool_name="test_tool",
                tool_args={},
                timeout_s=10,
                dry_run=False,
            ),
            "policy": PolicyConfig(),
            "tool_request": ToolRequest(
                tool_name="test_tool",
                args={},
                run_id=run_id,
                timeout_s=10,
            ),
            "tool_result": ToolResult(
                status=ToolStatus.SUCCESS,
                metrics=ToolMetrics(
                    duration_ms=500,
                    attempts=2,
                    retries_used=1,
                ),
            ),
            "budget": {
                "elapsed_ms_total": 500,
                "attempts_total": 2,
                "retries_used_total": 1,
                "short_circuited": False,
                "short_circuit_reason": None,
            },
        }

        result_state = service._collect_evidence(state)

        # Verify governance in evidence
        evidence = result_state["evidence"]
        assert "governance" in evidence

        gov = evidence["governance"]
        assert "budget" in gov
        assert "policy_limits" in gov
        assert gov["budget"]["elapsed_ms_total"] == 500
        assert gov["budget"]["attempts_total"] == 2
        assert gov["budget"]["retries_used_total"] == 1

        db.close()
