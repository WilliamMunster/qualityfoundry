"""
compiler
king 
2025/12/16
qualityfoundry
"""
from __future__ import annotations

import re
from qualityfoundry.models.schemas import (
    Action,
    ActionType,
    ExecutionRequest,
    Locator,
    TestCase,
)

# MVP：规则编译（稳定、可控）。后续可以在这里加 LLM + RAG 来补全 locator。
_RE_QUOTED = re.compile(r"[\"“](.*?)[\"”]")


def _extract_quoted(text: str) -> list[str]:
    return [x.strip() for x in _RE_QUOTED.findall(text or "") if x.strip()]


def compile_case_to_dsl(case: TestCase, base_url: str, headless: bool = True) -> ExecutionRequest:
    actions: list[Action] = []

    # 默认先 goto
    actions.append(Action(type=ActionType.GOTO, url=base_url))

    for s in case.steps:
        step_raw = s.step.strip()
        exp_raw = s.expected.strip()
        step = step_raw.lower()
        exp = exp_raw.lower()
        quoted_step = _extract_quoted(step_raw)
        quoted_exp = _extract_quoted(exp_raw)

        # 1) 打开/访问
        if any(k in step for k in ["open", "goto", "visit", "打开", "访问", "进入"]):
            url = quoted_step[0] if quoted_step and quoted_step[0].startswith("http") else base_url
            actions.append(Action(type=ActionType.GOTO, url=url))
            continue

        # 2) 点击（优先用引号中的按钮/链接文案，否则用整句）
        if any(k in step for k in ["click", "点击", "选择", "点选"]):
            target = quoted_step[0] if quoted_step else step_raw
            actions.append(
                Action(
                    type=ActionType.CLICK,
                    locator=Locator(strategy="text", value=target, exact=False),
                )
            )
            continue

        # 3) 输入（约定：字段名=值；或 在“字段”输入“值”）
        if any(k in step for k in ["enter", "input", "fill", "输入", "填写"]):
            field = None
            value = None

            if "=" in step_raw:
                left, right = step_raw.split("=", 1)
                field = left.strip()
                value = right.strip()
            else:
                # 取前两个引号段：字段、值
                if len(quoted_step) >= 2:
                    field, value = quoted_step[0], quoted_step[1]

            if field and value is not None:
                actions.append(
                    Action(
                        type=ActionType.FILL,
                        locator=Locator(strategy="label", value=field, exact=False),
                        value=value,
                    )
                )
            continue

        # 4) 断言（可见/显示/包含文本）
        if any(k in exp for k in ["显示", "可见", "看到", "is displayed", "should see", "visible"]):
            expected_text = quoted_exp[0] if quoted_exp else exp_raw
            actions.append(
                Action(
                    type=ActionType.ASSERT_TEXT,
                    locator=Locator(strategy="text", value=expected_text, exact=False),
                    value=expected_text,
                )
            )
            continue

    return ExecutionRequest(base_url=base_url, headless=headless, actions=actions)
