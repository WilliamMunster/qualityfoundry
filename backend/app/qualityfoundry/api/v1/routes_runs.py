"""QualityFoundry - Runs Routes

遗留的运行记录浏览 API（基于文件系统）。
注意：推荐使用 /api/v1/orchestrations/runs 获取带所有权过滤的运行列表。
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from qualityfoundry.services.artifacts.store import ArtifactStore
from qualityfoundry.api.deps.auth_deps import get_current_user, RequireOrchestrationRead
from qualityfoundry.database.user_models import User

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    dependencies=[Depends(get_current_user)],  # 整个 router 需要认证
)


def _store() -> ArtifactStore:
    root = Path(os.environ.get("QF_ARTIFACTS_DIR", "artifacts"))
    return ArtifactStore(root=root)


@router.get("")
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(RequireOrchestrationRead),
):
    """列出运行记录（文件系统快照）
    
    注意：此端点返回文件系统快照，所有权过滤由 /orchestrations/runs 提供。
    建议前端优先使用 /orchestrations/runs 端点。
    """
    try:
        return _store().list_runs(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}")
def get_run_detail(
    run_id: str,
    current_user: User = Depends(RequireOrchestrationRead),
):
    """获取运行详情"""
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
    current_user: User = Depends(RequireOrchestrationRead),
):
    """下载运行产物文件"""
    s = _store()
    try:
        p = s.resolve_file(run_id, path)
        return FileResponse(p)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
