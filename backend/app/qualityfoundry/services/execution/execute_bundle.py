"""
execute_bundle
king 
2025/12/16
qualityfoundry
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from qualityfoundry.models.schemas import (
    ExecuteBundleRequest,
    ExecuteBundleResponse,
    ExecuteBundleCompiledCase,
    ExecuteBundleCompileOptions,
    ExecutionRequest
)
from qualityfoundry.services.compile.compiler import compile_step_to_actions
from qualityfoundry.services.execution.executor import execute  # 复用你现有的执行器


@dataclass
class _CompileResult:
    case_id: str
    title: str
    actions: list[dict[str, Any]]
    warnings: list[str]


def _infer_base_url_from_actions(actions: list[dict[str, Any]]) -> str | None:
    """
    从 actions 中推断 base_url（用于执行器的一些相对路径/资源策略）。
    优先取第一条 goto 的 scheme+host。
    """
    for a in actions:
        if a.get("type") == "goto" and a.get("url"):
            p = urlparse(a["url"])
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}"
    return None


def _ensure_has_goto(actions: list[dict[str, Any]], fallback_url: str, timeout_ms: int) -> list[dict[str, Any]]:
    """
    保底：如果 actions 内没有 goto，则在开头补一个 goto，避免执行器无页面上下文。
    """
    for a in actions:
        if a.get("type") == "goto":
            return actions
    return [{"type": "goto", "url": fallback_url, "timeout_ms": timeout_ms}] + actions


def _compile_case_to_actions(
    *,
    case_id: str,
    title: str,
    steps: list[Any],
    options: ExecuteBundleCompileOptions,
) -> _CompileResult:
    """
    编译单条 Case：
    - 将每个 step.step 编译成 actions
    - strict=True 时，任何无法编译都视为失败（由上层转为 422）
    """
    all_actions: list[dict[str, Any]] = []
    warnings: list[str] = []

    for st in steps:
        # st 是 TestStep（Pydantic model）；兼容 dict/对象两种取值
        step_text = getattr(st, "step", None) or (st.get("step") if isinstance(st, dict) else None) or ""
        step_actions, step_warnings = compile_step_to_actions(step_text, options.default_timeout_ms)
        warnings.extend(step_warnings)
        all_actions.extend(step_actions)

    if options.strict and warnings:
        # strict：任何 warning 都当作失败（保持行为与 compile_bundle 一致）
        raise ValueError("; ".join(warnings) if warnings else "strict 模式下编译失败")

    return _CompileResult(case_id=case_id, title=title, actions=all_actions, warnings=warnings)


def execute_bundle(req: ExecuteBundleRequest) -> ExecuteBundleResponse:
    """
    一键执行入口：
    1) 选择 bundle 中某条 case
    2) 编译 steps -> actions（确定性规则）
    3) 调用现有 executor 执行 actions（Playwright），输出 evidence/artifacts
    """
    bundle = req.bundle
    cases = bundle.cases or []
    if not cases:
        return ExecuteBundleResponse(
            ok=False,
            compiled=None,
            execution={"ok": False, "started_at": None, "finished_at": None, "artifact_dir": None, "evidence": []},
            error="bundle.cases 为空，无法执行",
        )

    idx = req.case_index if req.case_index is not None else 0
    if idx < 0 or idx >= len(cases):
        return ExecuteBundleResponse(
            ok=False,
            compiled=None,
            execution={"ok": False, "started_at": None, "finished_at": None, "artifact_dir": None, "evidence": []},
            error=f"case_index 越界：{idx}，cases_count={len(cases)}",
        )

    case = cases[idx]
    case_id = getattr(case, "id", None) or (case.get("id") if isinstance(case, dict) else None) or "case_unknown"
    title = getattr(case, "title", None) or (case.get("title") if isinstance(case, dict) else None) or "Untitled Case"
    steps = getattr(case, "steps", None) or (case.get("steps") if isinstance(case, dict) else None) or []

    # 1) compile
    try:
        cr = _compile_case_to_actions(
            case_id=case_id,
            title=title,
            steps=steps,
            options=req.compile_options,
        )
    except ValueError as e:
        # 给 routes_compile_bundle 的风格：编译错误需要明确指出 case 信息
        return ExecuteBundleResponse(
            ok=False,
            compiled=ExecuteBundleCompiledCase(
                case_id=case_id,
                title=title,
                actions=[],
                warnings=[str(e)],
            ),
            execution=ExecutionResponse(ok=False, started_at=None, finished_at=None, artifact_dir=None, evidence=[]),
            error=f"编译失败：{str(e)}",
        )

    # 2) execute
    fallback_url = req.run.base_url or _infer_base_url_from_actions(cr.actions) or "https://example.com"
    actions = _ensure_has_goto(cr.actions, fallback_url=fallback_url, timeout_ms=req.compile_options.default_timeout_ms)

    exec_req = ExecutionRequest(
        base_url=req.run.base_url or _infer_base_url_from_actions(actions) or fallback_url,
        headless=req.run.headless,
        actions=actions,
    )

    exec_resp = execute(exec_req)

    # 兼容：exec_resp 可能是 Pydantic 模型，也可能是 dict
    exec_dict = exec_resp.model_dump() if hasattr(exec_resp, "model_dump") else dict(exec_resp)

    return ExecuteBundleResponse(
        ok=bool(exec_dict.get("ok")),
        compiled=ExecuteBundleCompiledCase(
            case_id=cr.case_id,
            title=cr.title,
            actions=actions,
            warnings=cr.warnings,
        ),
        execution=exec_dict,
        error=None if exec_dict.get("ok") else "执行失败（详见 evidence/error 字段）",
    )