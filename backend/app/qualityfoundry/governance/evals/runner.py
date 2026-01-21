"""QualityFoundry - Regression Runner

运行 Golden Dataset 并生成结果。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from qualityfoundry.governance.evals.models import (
    CaseResult,
    ExpectedResult,
    GoldenCase,
    GoldenDataset,
)
from qualityfoundry.governance import TraceCollector, evaluate_gate_with_hitl
from qualityfoundry.tools import ToolRequest
from qualityfoundry.tools.registry import get_registry, ToolNotFoundError

logger = logging.getLogger(__name__)


def check_expectation(evidence: dict[str, Any], expected: ExpectedResult) -> bool:
    """检查 evidence 是否满足期望"""
    # 检查 decision
    actual_decision = evidence.get("decision", "UNKNOWN")
    if actual_decision != expected.decision:
        return False

    # 检查 summary 字段（如果指定）
    if expected.summary:
        actual_summary = evidence.get("summary", {})
        for key, expected_value in expected.summary.items():
            if actual_summary.get(key) != expected_value:
                return False

    return True


async def _execute_tool_async(request: ToolRequest):
    """执行工具并返回结果"""
    from datetime import datetime, timezone
    from qualityfoundry.tools.contracts import ToolResult, ToolStatus

    registry = get_registry()

    try:
        tool_func = registry.get(request.tool_name)
    except ToolNotFoundError:
        now = datetime.now(timezone.utc)
        return ToolResult(
            status=ToolStatus.FAILED,
            stdout=None,
            stderr=f"Tool not found: {request.tool_name}",
            started_at=now,
            ended_at=now,
        )

    return await tool_func(request)


def run_single_case(
    case: GoldenCase,
    output_dir: Path,
) -> CaseResult:
    """运行单个测试用例"""
    run_id = str(uuid4())

    try:
        # 构建工具请求
        tool_request = ToolRequest(
            tool_name=case.options.get("tool_name", "run_pytest"),
            args={"test_path": case.options.get("test_path", "tests")},
            run_id=run_id,
            timeout_s=120,
        )

        # 执行工具（同步包装异步）
        tool_result = asyncio.run(_execute_tool_async(tool_request))

        # 收集证据
        collector = TraceCollector(
            run_id=run_id,
            input_nl=case.input_nl,
            environment={"case_id": case.id},
            artifact_root=output_dir,
        )
        collector.add_tool_result(tool_request.tool_name, tool_result)
        evidence = collector.collect()

        # 门禁决策
        gate_result = evaluate_gate_with_hitl(evidence)

        # 构建结果
        evidence_dict = evidence.model_dump()
        evidence_dict["decision"] = gate_result.decision.value

        passed = check_expectation(evidence_dict, case.expected)

        return CaseResult(
            case_id=case.id,
            run_id=run_id,
            actual_decision=gate_result.decision.value,
            expected_decision=case.expected.decision,
            passed=passed,
            policy_hash=None,  # GateResult doesn't have policy_hash yet
            git_sha=evidence.repro.git_sha if evidence.repro else None,
            evidence_path=str(output_dir / run_id / "evidence.json"),
        )

    except Exception as e:
        logger.exception(f"Case {case.id} failed with error")
        return CaseResult(
            case_id=case.id,
            run_id=run_id,
            actual_decision="ERROR",
            expected_decision=case.expected.decision,
            passed=False,
            evidence_path=str(output_dir / run_id / "evidence.json"),
            error_message=str(e),
        )


def run_all_cases(
    dataset: GoldenDataset,
    output_dir: Path,
) -> list[CaseResult]:
    """运行所有测试用例"""
    # 导入 runners 模块以自动注册工具
    import qualityfoundry.tools.runners  # noqa: F401
    
    results = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for case in dataset.cases:
        logger.info(f"Running case: {case.id}")
        result = run_single_case(case, output_dir)
        results.append(result)
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        logger.info(f"  {status}: {result.actual_decision} (expected: {result.expected_decision})")

    return results
