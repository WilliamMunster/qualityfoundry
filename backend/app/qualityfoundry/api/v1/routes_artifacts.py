"""QualityFoundry - Artifacts API Routes (PR-4)

Artifact 下载路由：安全地提供运行产物的下载服务。

GET /api/v1/artifacts/{run_id}/evidence.json - 下载证据文件
GET /api/v1/artifacts/{run_id}/{rel_path} - 下载任意产物

安全措施：
- 路径规范化防止目录遍历攻击
- 只允许访问 ARTIFACTS_ROOT 下的文件
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from qualityfoundry.tools.config import ARTIFACTS_ROOT

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _safe_resolve(run_id: UUID, rel_path: str) -> Path:
    """
    安全地解析文件路径。

    防止路径遍历攻击：
    1. 规范化基础目录和目标路径
    2. 验证目标路径在基础目录内
    3. 验证文件存在

    Args:
        run_id: 运行 ID
        rel_path: 相对路径

    Returns:
        解析后的安全路径

    Raises:
        HTTPException: 路径无效或文件不存在
    """
    # 规范化基础目录
    base = (Path(ARTIFACTS_ROOT) / str(run_id)).resolve()

    # 规范化目标路径
    target = (base / rel_path).resolve()

    # 安全检查：目标必须在基础目录内
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact path")

    # 文件存在检查
    if not target.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    return target


def _get_media_type(path: Path) -> str:
    """根据文件扩展名返回 MIME 类型"""
    suffix = path.suffix.lower()
    media_types = {
        ".json": "application/json",
        ".xml": "application/xml",
        ".html": "text/html",
        ".txt": "text/plain",
        ".log": "text/plain",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".zip": "application/zip",
        ".pdf": "application/pdf",
    }
    return media_types.get(suffix, "application/octet-stream")


@router.get("/{run_id}/evidence.json")
def get_evidence(run_id: UUID):
    """
    下载证据文件。

    Args:
        run_id: 运行 ID

    Returns:
        evidence.json 文件
    """
    path = _safe_resolve(run_id, "evidence.json")
    return FileResponse(
        path=path,
        media_type="application/json",
        filename="evidence.json",
    )


@router.get("/{run_id}/{rel_path:path}")
def get_artifact(run_id: UUID, rel_path: str):
    """
    下载任意产物。

    Args:
        run_id: 运行 ID
        rel_path: 相对路径（支持子目录）

    Returns:
        请求的文件
    """
    path = _safe_resolve(run_id, rel_path)
    return FileResponse(
        path=path,
        media_type=_get_media_type(path),
        filename=path.name,
    )
