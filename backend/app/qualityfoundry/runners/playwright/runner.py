"""QualityFoundry - Playwright Runner

职责：
- 接收受控 DSL（ExecutionRequest.actions）
- 按 action 顺序确定性执行
- 每一步产出证据（StepEvidence：是否成功、截图路径、错误信息）
- runner 不负责创建 run 目录与时间戳（交给 executor 统一管理）
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeoutError
from playwright.sync_api import sync_playwright

from qualityfoundry.models.schemas import Action, ActionType, ExecutionRequest, Locator, StepEvidence


def _resolve_locator(page, loc: Locator):
    """把 Locator 抽象映射成 Playwright locator。"""
    if loc.strategy == "text":
        return page.get_by_text(loc.value, exact=loc.exact)
    if loc.strategy == "role":
        # role 字段是可选的；当缺失时用 value 作为 role（兼容）
        role = loc.role or loc.value
        return page.get_by_role(role, name=loc.value if loc.role else None, exact=loc.exact)
    if loc.strategy == "label":
        return page.get_by_label(loc.value, exact=loc.exact)
    if loc.strategy == "testid":
        return page.get_by_test_id(loc.value)
    if loc.strategy == "css":
        return page.locator(loc.value)
    if loc.strategy == "xpath":
        # Playwright 支持 xpath= 前缀
        v = loc.value
        if not v.startswith("xpath="):
            v = "xpath=" + v
        return page.locator(v)

    raise ValueError(f"不支持的 locator.strategy={loc.strategy}")


def run_actions(req: ExecutionRequest, artifact_dir: Path) -> tuple[bool, list[StepEvidence]]:
    """统一 Runner 入口（唯一对外函数）。

    Args:
        req: ExecutionRequest（包含 actions / headless / base_url）
        artifact_dir: 本次 run 的产物目录（executor 已创建）

    Returns:
        (ok, evidence_list)
    """
    artifact_dir.mkdir(parents=True, exist_ok=True)

    ok_all = True
    evidence: list[StepEvidence] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=req.headless)
        context = browser.new_context()
        page = context.new_page()

        # 若 caller 给了 base_url，可作为默认跳转目标（但不强制）
        if req.base_url:
            page.goto(req.base_url, timeout=30_000)

        for idx, action in enumerate(req.actions):
            step_ok = True
            err: str | None = None
            shot_path = artifact_dir / f"step_{idx:03d}.png"

            try:
                _apply_action(page, action)
            except PWTimeoutError as e:
                step_ok = False
                ok_all = False
                err = f"Playwright 超时：{str(e)}"
            except Exception as e:
                step_ok = False
                ok_all = False
                err = str(e)
            finally:
                # 无论成功失败都截图，便于定位
                try:
                    page.screenshot(path=str(shot_path), full_page=True)
                    shot = str(shot_path)
                except Exception as e:
                    shot = None
                    # 截图失败也要记录下来（但不覆盖主错误）
                    if err is None:
                        err = f"截图失败：{str(e)}"

            evidence.append(
                StepEvidence(
                    index=idx,
                    action=action,
                    ok=step_ok,
                    screenshot=shot,
                    error=err,
                )
            )

        context.close()
        browser.close()

    return ok_all, evidence


def _apply_action(page, action: Action) -> None:
    """执行单个 DSL Action。"""
    t = action.type

    # 1) goto
    if t == ActionType.GOTO:
        if not action.url:
            raise ValueError("goto 缺少 url")
        page.goto(action.url, timeout=action.timeout_ms)
        return

    # 2) click
    if t == ActionType.CLICK:
        if not action.locator:
            raise ValueError("click 缺少 locator")
        _resolve_locator(page, action.locator).click(timeout=action.timeout_ms)
        return

    # 3) fill
    if t == ActionType.FILL:
        if not action.locator:
            raise ValueError("fill 缺少 locator")
        if action.value is None:
            raise ValueError("fill 缺少 value")
        _resolve_locator(page, action.locator).fill(action.value, timeout=action.timeout_ms)
        return

    # 4) assert_text
    if t == ActionType.ASSERT_TEXT:
        if not action.value:
            raise ValueError("assert_text 缺少 value")
        # 用 get_by_text 做一个确定性断言
        page.get_by_text(action.value, exact=False).wait_for(timeout=action.timeout_ms)
        return

    # 5) wait（简单 sleep，单位 ms）
    if t == ActionType.WAIT:
        page.wait_for_timeout(action.timeout_ms)
        return

    raise ValueError(f"不支持的 action.type={t}")