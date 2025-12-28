from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from qualityfoundry.services.artifacts.store import ArtifactStore

router = APIRouter(prefix="/runs", tags=["runs"])


def _store() -> ArtifactStore:
    root = Path(os.environ.get("QF_ARTIFACTS_DIR", "artifacts"))
    return ArtifactStore(root=root)


@router.get("")
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        return _store().list_runs(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}")
def get_run_detail(run_id: str):
    s = _store()
    try:
        summary = s.get_run(run_id)
        files = s.list_files(run_id)
        return {"summary": summary, "files": files}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="run not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}/file")
def get_run_file(
    run_id: str,
    path: str = Query(..., min_length=1, description="run 内相对路径，例如 step_000.png 或 http/execute.request.json"),
):
    s = _store()
    try:
        p = s.resolve_file(run_id, path)
        return FileResponse(p)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
