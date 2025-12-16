from __future__ import annotations
import re
from typing import Any


def _action_goto(url: str, timeout_ms: int) -> dict[str, Any]:
    return {"type": "goto", "url": url, "timeout_ms": timeout_ms}


def _action_click_text(text: str, timeout_ms: int) -> dict[str, Any]:
    return {"type": "click", "locator": {"strategy": "text", "value": text, "exact": False}, "timeout_ms": timeout_ms}


def _action_fill_placeholder(placeholder: str, value: str, timeout_ms: int) -> dict[str, Any]:
    return {"type": "fill", "locator": {"strategy": "placeholder", "value": placeholder}, "value": value,
            "timeout_ms": timeout_ms}


def _action_assert_text(text: str, timeout_ms: int) -> dict[str, Any]:
    return {"type": "assert_text", "locator": {"strategy": "text", "value": text, "exact": False}, "value": text,
            "timeout_ms": timeout_ms}


def compile_step_to_actions(step_text: str, timeout_ms: int) -> tuple[list[dict[str, Any]], list[str]]:
    """
    将自然语言 step 编译为受控 DSL（确定性规则）。
    返回：(actions, warnings)
    """
    s = (step_text or "").strip()
    warnings: list[str] = []

    # 规则 1：打开/访问 URL
    m = re.search(r"(https?://\S+)", s)
    if re.search(r"^(打开|访问|进入|跳转到)\b", s) and m:
        return [_action_goto(m.group(1), timeout_ms)], warnings

    # 规则 2：点击（按文本）
    # 示例：点击 登录 / Click Login
    m = re.search(r"^(点击|单击|click)\s+(.+)$", s, flags=re.IGNORECASE)
    if m:
        text = m.group(2).strip().strip('"').strip("'")
        return [_action_click_text(text, timeout_ms)], warnings

    # 规则 3：输入（按 placeholder）
    # 示例：在 Username 输入 user1
    m = re.search(r"^(在)?\s*(.+?)\s*(输入|填写)\s*(.+)$", s)
    if m:
        placeholder = m.group(2).strip().strip('"').strip("'")
        value = m.group(4).strip().strip('"').strip("'")
        return [_action_fill_placeholder(placeholder, value, timeout_ms)], warnings

    # 规则 4：断言文本出现
    # 示例：应看到 Example Domain / 看到 “登录成功”
    m = re.search(r"(应看到|看到|显示)\s*(.+)$", s)
    if m:
        text = m.group(2).strip().strip('"').strip("'")
        return ([_action_assert_text(text, timeout_ms)], warnings)

    # 兜底：无法编译，给 warning（strict 模式由上层决定是否失败）
    warnings.append(f"无法编译步骤：{s}")
    return [], warnings
