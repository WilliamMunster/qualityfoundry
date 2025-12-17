"""QualityFoundry - Execution Service（执行服务）

职责：
- 统一对外执行入口：execute(req)
- 创建本次执行 artifacts/run_xxx 目录
- 记录 started_at / finished_at
- 调用 Runner 执行（Playwright）
- 组装统一返回结构（ExecutionResponse）
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from qualityfoundry.core.config import settings
from qualityfoundry.models.schemas import ExecutionRequest, ExecutionResponse
from qualityfoundry.runners.playwright.runner import run_actions


def _new_run_dir(base: Path) -> Path:
    """生成本次 run 的产物目录：artifacts/run_YYYYmmddTHHMMSSZ"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return base / f"run_{ts}"


def execute(req: ExecutionRequest) -> ExecutionResponse:
    """统一执行入口（API / bundle / CLI 都应调用这里）。"""
    started = datetime.now(timezone.utc)

    # 兼容兜底：即使 Settings 没带该字段，也不会炸（默认 artifacts）
    artifacts_root = Path(getattr(settings, "artifacts_dir", "artifacts"))
    run_dir = _new_run_dir(artifacts_root)
    run_dir.mkdir(parents=True, exist_ok=True)

    ok, evidence = run_actions(req=req, artifact_dir=run_dir)

    finished = datetime.now(timezone.utc)

    return ExecutionResponse(
        ok=ok,
        started_at=started,
        finished_at=finished,
        artifact_dir=str(run_dir),
        evidence=evidence,
    )