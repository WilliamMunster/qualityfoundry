from __future__ import annotations

"""
QualityFoundry - Step Compiler (Deterministic)

职责：
- 将自然语言步骤（step）编译为受控 DSL（actions 列表）
- 规则优先级明确、确定性强、可测试、可扩展
- 不依赖 LLM，作为 MVP 稳定基座

设计原则：
1) 先匹配“更确定、更具体”的规则（如 Open URL / See text），再匹配泛化规则
2) 编译失败时不抛异常，只返回 warnings；是否严格失败由上层（compile_bundle strict）决定
3) 输出 action 结构应与 runner 侧 schemas 对齐（type、locator、timeout_ms 等）
"""

import re
from typing import Any


# -----------------------------
# Action builders（统一封装 DSL 输出）
# -----------------------------

def _action_goto(url: str, timeout_ms: int) -> dict[str, Any]:
    """导航到指定 URL。"""
    return {"type": "goto", "url": url, "timeout_ms": timeout_ms}


def _action_click_text(text: str, timeout_ms: int) -> dict[str, Any]:
    """按可见文本点击（locator 使用 text 策略）。"""
    return {
        "type": "click",
        "locator": {"strategy": "text", "value": text, "exact": False},
        "timeout_ms": timeout_ms,
    }


def _action_fill_placeholder(placeholder: str, value: str, timeout_ms: int) -> dict[str, Any]:
    """按 input 的 placeholder 填写。"""
    return {
        "type": "fill",
        "locator": {"strategy": "placeholder", "value": placeholder},
        "value": value,
        "timeout_ms": timeout_ms,
    }


def _action_assert_text(text: str, timeout_ms: int) -> dict[str, Any]:
    """断言页面出现某段文本（MVP：contains）。"""
    return {
        "type": "assert_text",
        "locator": {"strategy": "text", "value": text, "exact": False},
        "value": text,
        "timeout_ms": timeout_ms,
    }


# -----------------------------
# Compiler（规则编译）
# -----------------------------

def compile_step_to_actions(step_text: str, timeout_ms: int) -> tuple[list[dict[str, Any]], list[str]]:
    """
    将自然语言 step 编译为受控 DSL（确定性规则）。

    返回：
    - actions: 编译后的 DSL actions
    - warnings: 编译告警（strict 模式由上层决定是否失败）
    """
    s = (step_text or "").strip()
    warnings: list[str] = []

    if not s:
        warnings.append("步骤为空，无法编译")
        return ([], warnings)

    # ============================================================
    # A. 英文规则（用于 CI 冒烟与通用英文步骤）
    # ============================================================

    # A1) Open <url>
    m = re.search(r"^open\s+(https?://\S+)\s*$", s, flags=re.IGNORECASE)
    if m:
        return ([_action_goto(m.group(1), timeout_ms)], warnings)

    # A2) See <text>
    m = re.search(r"^see\s+(.+)$", s, flags=re.IGNORECASE)
    if m:
        text = m.group(1).strip().strip('"').strip("'")
        return ([_action_assert_text(text, timeout_ms)], warnings)

    # A3) Click <text>
    m = re.search(r"^click\s+(.+)$", s, flags=re.IGNORECASE)
    if m:
        text = m.group(1).strip().strip('"').strip("'")
        return ([_action_click_text(text, timeout_ms)], warnings)

    # ============================================================
    # B. 中文规则（常见句式）
    # ============================================================

    # B1) 打开/访问/进入/跳转到 + URL
    m = re.search(r"(https?://\S+)", s)
    if re.search(r"^(打开|访问|进入|跳转到)\b", s) and m:
        return ([_action_goto(m.group(1), timeout_ms)], warnings)

    # B2) 点击/单击 + 文本（同时兼容 click）
    m = re.search(r"^(点击|单击|click)\s+(.+)$", s, flags=re.IGNORECASE)
    if m:
        text = m.group(2).strip().strip('"').strip("'")
        return ([_action_click_text(text, timeout_ms)], warnings)

    # B3) 输入/填写（按 placeholder）
    m = re.search(r"^(在)?\s*(.+?)\s*(输入|填写)\s*(.+)$", s)
    if m:
        placeholder = m.group(2).strip().strip('"').strip("'")
        value = m.group(4).strip().strip('"').strip("'")
        return ([_action_fill_placeholder(placeholder, value, timeout_ms)], warnings)

    # B4) 断言文本出现：应看到/看到/显示
    m = re.search(r"^(应看到|看到|显示)\s*(.+)$", s)
    if m:
        text = m.group(2).strip().strip('"').strip("'")
        return ([_action_assert_text(text, timeout_ms)], warnings)

    # ============================================================
    # C. 兜底策略
    # ============================================================

    warnings.append(f"无法编译步骤：{s}")
    return ([], warnings)
