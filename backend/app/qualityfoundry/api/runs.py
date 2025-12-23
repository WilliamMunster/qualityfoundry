"""
runs
king 
2025/12/23
qualityfoundry
"""
# backend/app/qualityfoundry/api/runs.py
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from qualityfoundry.services.artifacts.store import ArtifactStore

router = APIRouter(prefix="/api/v1", tags=["runs"])


def _store() -> ArtifactStore:
    root = Path(__import__("os").getenv("QF_ARTIFACTS_DIR", "artifacts"))
    return ArtifactStore(root)


@router.get("/runs")
def list_runs(limit: int = 20, offset: int = 0):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return {"items": [r.__dict__ for r in _store().list_runs(limit, offset)], "limit": limit, "offset": offset}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    try:
        r = _store().get_run(run_id)
        return r.__dict__
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/files")
def list_files(run_id: str):
    try:
        return {"items": _store().list_files(run_id)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/files/{file_path:path}")
def get_file(run_id: str, file_path: str):
    try:
        p = _store().resolve_file(run_id, file_path)
        return FileResponse(path=str(p), filename=p.name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
