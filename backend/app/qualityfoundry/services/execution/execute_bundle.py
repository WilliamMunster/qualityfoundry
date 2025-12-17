"""
QualityFoundry - Execute Bundle Service（bundle 一键执行）

职责：
- 输入：ExecuteBundleRequest（包含 bundle + 选中的 case_index + compile/run options）
- 流程：compile（确定性）-> execute（runner）-> 返回统一 ExecuteBundleResponse
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from qualityfoundry.models.schemas import (
    ExecuteBundleRequest,
    ExecuteBundleResponse,
    CaseExecutionResult,
    ExecutionRequest,
)
from qualityfoundry.services.execution.executor import execute
from qualityfoundry.services.compile.bundle_compiler import compile_bundle, CompileBundleError


def _infer_base_url(actions: list[dict[str, Any]]) -> str | None:
    """从 actions 里推断 base_url（优先取第一个 goto.url）。"""
    for a in actions:
        if a.get("type") == "goto" and a.get("url"):
            return str(a["url"])
    return None


def execute_bundle(req: ExecuteBundleRequest) -> ExecuteBundleResponse:
    started = datetime.now(timezone.utc)

    bundle = req.bundle
    cases = bundle.cases or []
    if not cases:
        return ExecuteBundleResponse(
            ok=False,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            artifact_dir=None,
            results=[
                CaseExecutionResult(
                    case_id="",
                    title="",
                    ok=False,
                    warnings=["bundle.cases 为空，无法执行"],
                    error="bundle.cases 为空",
                    execution=None,
                )
            ],
        )

    idx = req.case_index or 0
    if idx < 0 or idx >= len(cases):
        return ExecuteBundleResponse(
            ok=False,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            artifact_dir=None,
            results=[
                CaseExecutionResult(
                    case_id="",
                    title="",
                    ok=False,
                    warnings=[f"case_index 越界：{idx}，cases_count={len(cases)}"],
                    error="case_index 越界",
                    execution=None,
                )
            ],
        )

    target_case = cases[idx]

    # 1) compile（确定性）
    try:
        compiled_cases = compile_bundle(
            cases=[target_case],
            default_timeout_ms=req.compile_options.default_timeout_ms,
            strict=req.compile_options.strict,
        )
        compiled = compiled_cases[0]
    except CompileBundleError as e:
        finished = datetime.now(timezone.utc)
        return ExecuteBundleResponse(
            ok=False,
            started_at=started,
            finished_at=finished,
            artifact_dir=None,
            results=[
                CaseExecutionResult(
                    case_id=e.case_id,
                    title=e.title,
                    ok=False,
                    warnings=[],
                    error="编译失败：" + "; ".join(e.errors),
                    execution=None,
                )
            ],
        )
    except Exception as e:
        finished = datetime.now(timezone.utc)
        return ExecuteBundleResponse(
            ok=False,
            started_at=started,
            finished_at=finished,
            artifact_dir=None,
            results=[
                CaseExecutionResult(
                    case_id=str(getattr(target_case, "id", "")),
                    title=str(getattr(target_case, "title", "")),
                    ok=False,
                    warnings=[str(e)],
                    error="编译异常",
                    execution=None,
                )
            ],
        )

    # 2) execute（统一入口：services.execution.executor.execute）
    actions = compiled.actions or []
    base_url = req.run.base_url or _infer_base_url(actions) or "https://example.com"

    exec_req = ExecutionRequest(
        base_url=base_url,
        headless=req.run.headless,
        actions=actions,  # runner 侧按 schemas.Action 执行；这里 actions 已是 dict（你的 runner 已适配）
    )

    exec_resp = execute(exec_req)

    finished = datetime.now(timezone.utc)

    results = [
        CaseExecutionResult(
            case_id=compiled.case_id,
            title=compiled.title,
            ok=exec_resp.ok,
            warnings=compiled.warnings or [],
            error=None if exec_resp.ok else "执行失败",
            execution=exec_resp,
        )
    ]

    return ExecuteBundleResponse(
        ok=all(r.ok for r in results),
        started_at=started,
        finished_at=finished,
        artifact_dir=exec_resp.artifact_dir,
        results=results,
    )
