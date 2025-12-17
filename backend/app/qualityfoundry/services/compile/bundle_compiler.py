"""
QualityFoundry - Bundle Compiler（确定性编译器封装）

职责：
- 提供 compile_bundle() 给 execute_bundle 复用（避免依赖 routes 层或不确定的模块路径）
- 基于 compile_step_to_actions 做“自然语言步骤 -> 受控 DSL actions”的编译
- strict=True 时：任意步骤无法编译即失败（更适合 CI）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qualityfoundry.models.schemas import ExecuteBundleCompiledCase
from qualityfoundry.services.compile.compiler import compile_step_to_actions


@dataclass
class CompileBundleError(Exception):
    """编译失败时抛出：携带 case 信息，便于上层组装错误返回。"""

    case_id: str
    title: str
    errors: list[str]

    def __str__(self) -> str:
        return f"CompileBundleError(case_id={self.case_id}, title={self.title}, errors={self.errors})"


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """兼容 dict / pydantic model 的取值方式。"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def compile_bundle(
    *,
    cases: list[Any],
    default_timeout_ms: int = 15000,
    strict: bool = True,
) -> list[ExecuteBundleCompiledCase]:
    """
    编译一组 cases -> compiled_cases（每条 case 对应 actions/warnings）。
    - cases: TestCase 列表（可为 dict 或 Pydantic model）
    - strict: True 则遇到无法编译的步骤直接抛 CompileBundleError
    """
    compiled_cases: list[ExecuteBundleCompiledCase] = []

    for c in cases:
        case_id = str(_get(c, "id", ""))
        title = str(_get(c, "title", ""))

        steps = _get(c, "steps", []) or []
        actions: list[dict[str, Any]] = []
        warnings: list[str] = []

        for st in steps:
            step_text = str(_get(st, "step", "")).strip()
            if not step_text:
                warnings.append("无法编译步骤：<empty step>")
                continue

            step_actions, step_warnings = compile_step_to_actions(step_text, default_timeout_ms)
            if step_warnings:
                warnings.extend(step_warnings)

            # 注意：compile_step_to_actions 可能返回空 actions + warnings
            if step_actions:
                actions.extend(step_actions)

        # strict：任何无法编译的步骤都失败（以 warnings 里“无法编译步骤：”为准）
        if strict:
            hard_errors = [w for w in warnings if w.startswith("无法编译步骤：")]
            if hard_errors:
                raise CompileBundleError(case_id=case_id, title=title, errors=hard_errors)

        compiled_cases.append(
            ExecuteBundleCompiledCase(
                case_id=case_id,
                title=title,
                actions=actions,
                warnings=warnings,
            )
        )

    return compiled_cases
