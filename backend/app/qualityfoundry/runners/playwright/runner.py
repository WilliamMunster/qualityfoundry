from __future__ import annotations

import json
from pathlib import Path
from typing import List

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

from qualityfoundry.models.schemas import Action, ActionType, ExecutionRequest, StepEvidence, Locator

def _resolve_locator(page, loc: Locator):
    strategy = loc.strategy
    value = loc.value

    if strategy == "role":
        # role strategy requires a role name; fallback to value if role isn't provided
        role = loc.role or value
        return page.get_by_role(role, name=None if loc.exact is False else value)
    if strategy == "label":
        return page.get_by_label(value, exact=loc.exact)
    if strategy == "text":
        return page.get_by_text(value, exact=loc.exact)
    if strategy == "testid":
        return page.get_by_test_id(value)
    if strategy == "css":
        return page.locator(value)
    if strategy == "xpath":
        return page.locator(f"xpath={value}")
    raise ValueError(f"Unsupported locator strategy: {strategy}")

def _screenshot(page, artifact_dir: Path, idx: int) -> str:
    path = artifact_dir / f"step_{idx:03d}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)

def run_actions(req: ExecutionRequest, artifact_dir: Path) -> List[StepEvidence]:
    logs_path = artifact_dir / "run_log.jsonl"

    evidence: List[StepEvidence] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=req.headless)
        context = browser.new_context()
        page = context.new_page()

        def log(obj):
            logs_path.open("a", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False) + "\n")

        for i, action in enumerate(req.actions):
            ev = StepEvidence(index=i, action=action, ok=True)
            try:
                if action.type == ActionType.GOTO:
                    url = action.url or req.base_url
                    if not url:
                        raise ValueError("Missing url/base_url for goto")
                    page.goto(url, timeout=action.timeout_ms, wait_until="domcontentloaded")

                elif action.type == ActionType.CLICK:
                    if not action.locator:
                        raise ValueError("Missing locator for click")
                    _resolve_locator(page, action.locator).click(timeout=action.timeout_ms)

                elif action.type == ActionType.FILL:
                    if not action.locator:
                        raise ValueError("Missing locator for fill")
                    if action.value is None:
                        raise ValueError("Missing value for fill")
                    _resolve_locator(page, action.locator).fill(action.value, timeout=action.timeout_ms)

                elif action.type == ActionType.SELECT:
                    if not action.locator:
                        raise ValueError("Missing locator for select")
                    if action.value is None:
                        raise ValueError("Missing value for select")
                    _resolve_locator(page, action.locator).select_option(action.value, timeout=action.timeout_ms)

                elif action.type == ActionType.CHECK:
                    if not action.locator:
                        raise ValueError("Missing locator for check")
                    _resolve_locator(page, action.locator).check(timeout=action.timeout_ms)

                elif action.type == ActionType.UNCHECK:
                    if not action.locator:
                        raise ValueError("Missing locator for uncheck")
                    _resolve_locator(page, action.locator).uncheck(timeout=action.timeout_ms)

                elif action.type == ActionType.WAIT:
                    # value as milliseconds or a selector
                    if action.value and action.value.isdigit():
                        page.wait_for_timeout(int(action.value))
                    else:
                        page.wait_for_timeout(500)

                elif action.type == ActionType.ASSERT_TEXT:
                    if not action.locator:
                        raise ValueError("Missing locator for assert_text")
                    if action.value is None:
                        raise ValueError("Missing expected text for assert_text")
                    loc = _resolve_locator(page, action.locator)
                    loc.wait_for(timeout=action.timeout_ms, state="visible")
                    actual = loc.inner_text(timeout=action.timeout_ms)
                    if action.value not in actual:
                        raise AssertionError(f"Expected text not found. expected={action.value!r} actual={actual!r}")

                elif action.type == ActionType.ASSERT_VISIBLE:
                    if not action.locator:
                        raise ValueError("Missing locator for assert_visible")
                    _resolve_locator(page, action.locator).wait_for(timeout=action.timeout_ms, state="visible")

                else:
                    raise ValueError(f"Unsupported action type: {action.type}")

                ev.screenshot = _screenshot(page, artifact_dir, i)
                log({"index": i, "action": action.model_dump(), "ok": True, "screenshot": ev.screenshot})

            except (PWTimeoutError, AssertionError, Exception) as e:
                ev.ok = False
                ev.error = str(e)
                try:
                    ev.screenshot = _screenshot(page, artifact_dir, i)
                except Exception:
                    ev.screenshot = None
                log({"index": i, "action": action.model_dump(), "ok": False, "error": ev.error, "screenshot": ev.screenshot})
                evidence.append(ev)
                # fail-fast for MVP; later you can support "continue-on-failure"
                break

            evidence.append(ev)

        context.close()
        browser.close()

    return evidence
