from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from qualityfoundry.core.config import settings
from qualityfoundry.models.schemas import ExecutionRequest, ExecutionResult, StepEvidence
from qualityfoundry.runners.playwright.runner import run_actions

def execute(req: ExecutionRequest) -> ExecutionResult:
    started = datetime.now(timezone.utc)
    artifact_root = Path(settings.ARTIFACT_DIR)
    artifact_root.mkdir(parents=True, exist_ok=True)

    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = artifact_root / f"run_{run_id}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    evidence = []
    ok = True
    try:
        evidences = run_actions(req, artifact_dir=artifact_dir)
        evidence = list(evidences)
        ok = all(e.ok for e in evidence)
    except Exception as e:
        ok = False
        evidence.append(
            StepEvidence(index=-1, action=req.actions[0] if req.actions else None, ok=False, error=str(e))
        )

    finished = datetime.now(timezone.utc)
    return ExecutionResult(
        ok=ok,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        artifact_dir=str(artifact_dir),
        evidence=evidence,
    )
