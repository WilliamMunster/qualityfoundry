"""QualityFoundry - Runs Routes (Legacy)

遗留的运行记录浏览 API（基于文件系统）。

!!! DEPRECATED !!!
推荐使用 /api/v1/orchestrations/runs 获取带所有权过滤的运行列表。
此端点将在未来版本中移除。
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse

from qualityfoundry.services.artifacts.store import ArtifactStore
from qualityfoundry.api.deps.auth_deps import get_current_user, RequireOrchestrationRead
from qualityfoundry.database.user_models import User


# Deprecation headers（标准化）
DEPRECATION_HEADERS = {
    "Deprecation": "true",
    "X-Deprecated": "Use /api/v1/orchestrations/runs instead",
    "Link": '</api/v1/orchestrations/runs>; rel="successor-version"',
}


router = APIRouter(
    prefix="/runs",
    tags=["runs (legacy)"],
    dependencies=[Depends(get_current_user)],  # 整个 router 需要认证
)


def _store() -> ArtifactStore:
    root = Path(os.environ.get("QF_ARTIFACTS_DIR", "artifacts"))
    return ArtifactStore(root=root)


def _add_deprecation_headers(response: Response) -> None:
    """为响应添加 deprecation headers"""
    for key, value in DEPRECATION_HEADERS.items():
        response.headers[key] = value


@router.get("")
def list_runs(
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(RequireOrchestrationRead),
):
    """列出运行记录（文件系统快照）
    
    ⚠️ DEPRECATED: 请使用 /api/v1/orchestrations/runs
    
    此端点返回文件系统快照，无所有权过滤。
    推荐使用 /orchestrations/runs 端点获取带权限的列表。
    """
    _add_deprecation_headers(response)
    try:
        runs = _store().list_runs(limit=limit, offset=offset)
        # 添加 run_kind 标识
        for run in runs:
            run["run_kind"] = "legacy_artifact"
        return runs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}")
def get_run_detail(
    run_id: str,
    response: Response,
    current_user: User = Depends(RequireOrchestrationRead),
):
    """获取运行详情
    
    ⚠️ DEPRECATED: 请使用 /api/v1/orchestrations/runs/{id}
    """
    _add_deprecation_headers(response)
    s = _store()
    try:
        summary = s.get_run(run_id)
        files = s.list_files(run_id)
        # 添加 run_kind 标识
        summary["run_kind"] = "legacy_artifact"
        return {"summary": summary, "files": files, "run_kind": "legacy_artifact"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="run not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}/file")
def get_run_file(
    run_id: str,
    response: Response,
    path: str = Query(..., min_length=1, description="run 内相对路径，例如 step_000.png 或 http/execute.request.json"),
    current_user: User = Depends(RequireOrchestrationRead),
):
    """下载运行产物文件
    
    ⚠️ DEPRECATED: 请使用 /api/v1/artifacts/{run_id}/*
    """
    _add_deprecation_headers(response)
    s = _store()
    try:
        p = s.resolve_file(run_id, path)
        # FileResponse 不支持直接设置 headers，需要通过 Response 设置
        return FileResponse(p, headers=dict(DEPRECATION_HEADERS))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

