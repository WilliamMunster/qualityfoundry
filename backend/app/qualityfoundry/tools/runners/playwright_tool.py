"""QualityFoundry - Playwright Tool

将现有的 Playwright runner 包装为统一的 Tool 接口。

使用方式：
    request = ToolRequest(
        tool_name="run_playwright",
        run_id=uuid4(),
        args={
            "actions": [...],  # DSL actions
            "base_url": "https://example.com",
            "headless": True,
        }
    )
    result = await run_playwright(request)
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from qualityfoundry.models.schemas import Action, ExecutionRequest, StepEvidence
from qualityfoundry.runners.playwright.runner import run_actions
from qualityfoundry.tools.base import ToolExecutionContext, log_tool_result
from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolRequest,
    ToolResult,
)

logger = logging.getLogger(__name__)

# 线程池用于运行同步的 Playwright
_executor = ThreadPoolExecutor(max_workers=4)


async def run_playwright(request: ToolRequest) -> ToolResult:
    """Playwright 工具：执行 DSL actions

    Args:
        request: ToolRequest，args 包含：
            - actions: list[dict] - DSL 动作列表
            - base_url: str (可选) - 基础 URL
            - headless: bool (可选, 默认 True) - 是否无头模式
            - enable_tracing: bool (可选, 默认 True) - 是否启用 trace 收集

    Returns:
        ToolResult: 统一的执行结果，artifacts 包含 screenshots + trace.zip
    """
    async with ToolExecutionContext(request) as ctx:
        try:
            # 解析参数
            args = request.args
            actions_raw = args.get("actions", [])
            base_url = args.get("base_url")
            headless = args.get("headless", True)
            enable_tracing = args.get("enable_tracing", True)

            if not actions_raw:
                return ctx.failed("No actions provided")

            # 转换为 Action 对象
            actions = [Action.model_validate(a) for a in actions_raw]

            # 构建 ExecutionRequest
            exec_request = ExecutionRequest(
                actions=actions,
                base_url=base_url,
                headless=headless,
            )

            # 在线程池中运行同步的 Playwright（带超时）
            loop = asyncio.get_event_loop()

            try:
                ok, evidence, trace_path = await asyncio.wait_for(
                    loop.run_in_executor(
                        _executor,
                        lambda: run_actions(exec_request, ctx.artifact_dir, enable_tracing),
                    ),
                    timeout=request.timeout_s,
                )
            except asyncio.TimeoutError:
                # 尝试收集已有的 artifacts
                ctx.collect_artifacts()
                return ctx.timeout()

            # 收集 artifacts（截图等）
            artifacts = _convert_evidence_to_artifacts(evidence, ctx.artifact_dir)
            ctx.add_artifacts(artifacts)

            # 添加 trace.zip artifact（PR-2 增强）
            if trace_path:
                trace_file = Path(trace_path)
                if trace_file.exists():
                    trace_artifact = ArtifactRef.from_file(trace_file, ArtifactType.TRACE)
                    ctx.add_artifact(trace_artifact)
                    logger.info(f"Added trace artifact: {trace_path}")

            # 记录产物审计日志
            if ctx._artifacts:
                try:
                    from qualityfoundry.database.config import SessionLocal
                    from qualityfoundry.services.audit_service import write_artifact_collected_event
                    
                    with SessionLocal() as db:
                        write_artifact_collected_event(
                            db,
                            run_id=request.run_id,
                            tool_name="run_playwright",
                            artifacts=ctx._artifacts,
                            scope=["screenshots", "traces"],
                        )
                except Exception:
                    logger.warning("Failed to log playwright artifact audit event", exc_info=True)

            # 更新 metrics
            ctx.update_metrics(
                steps_total=len(evidence),
                steps_passed=sum(1 for e in evidence if e.ok),
                steps_failed=sum(1 for e in evidence if not e.ok),
            )

            # 构建结果
            if ok:
                result = ctx.success(
                    raw_output={
                        "ok": ok,
                        "evidence": [e.model_dump() for e in evidence],
                        "trace_path": trace_path,
                    }
                )
            else:
                # 找到第一个失败的步骤
                failed_step = next((e for e in evidence if not e.ok), None)
                error_msg = failed_step.error if failed_step else "Execution failed"
                result = ctx.failed(
                    error_message=error_msg,
                )
                result.raw_output = {
                    "ok": ok,
                    "evidence": [e.model_dump() for e in evidence],
                    "trace_path": trace_path,
                }

            log_tool_result(result, "run_playwright")
            return result

        except Exception as e:
            logger.exception("Playwright tool failed")
            # 尝试收集已有的 artifacts
            ctx.collect_artifacts()
            return ctx.failed(error_message=str(e))


def _convert_evidence_to_artifacts(
    evidence: list[StepEvidence],
    artifact_dir: Path,
) -> list[ArtifactRef]:
    """将 StepEvidence 转换为 ArtifactRef 列表"""
    artifacts: list[ArtifactRef] = []

    for ev in evidence:
        if ev.screenshot:
            path = Path(ev.screenshot)
            if path.exists():
                ref = ArtifactRef.from_file(path, ArtifactType.SCREENSHOT)
                ref.metadata = {
                    "step_index": ev.index,
                    "step_ok": ev.ok,
                }
                artifacts.append(ref)

    return artifacts


# 工具元数据（用于注册）
TOOL_METADATA = {
    "name": "run_playwright",
    "description": "Execute Playwright DSL actions for browser automation",
    "version": "1.0.0",
    "tags": ["browser", "automation", "testing"],
}
