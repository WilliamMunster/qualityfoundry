"""MCP Server Tool Definitions

只读、安全的工具暴露，用于 MCP Server。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from qualityfoundry.tools.config import get_artifacts_root
from qualityfoundry.governance.tracing.collector import load_evidence

logger = logging.getLogger(__name__)

# 安全工具目录：只暴露只读操作
SAFE_TOOLS = {
    "get_evidence": {
        "description": "获取指定运行的 evidence.json 内容",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "运行 ID (UUID)"}
            },
            "required": ["run_id"],
        },
    },
    "list_artifacts": {
        "description": "列出指定运行的所有产物文件",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "运行 ID (UUID)"}
            },
            "required": ["run_id"],
        },
    },
    "get_artifact_content": {
        "description": "获取指定产物文件的内容（仅文本文件）",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "运行 ID (UUID)"},
                "rel_path": {"type": "string", "description": "相对路径"},
            },
            "required": ["run_id", "rel_path"],
        },
    },
}


def _validate_path(run_id: str, rel_path: str) -> Path:
    """验证路径安全性，返回解析后的路径"""
    if rel_path.startswith("/") or rel_path.startswith("\\"):
        raise ValueError("Absolute paths not allowed")
    if ".." in rel_path.split("/") or ".." in rel_path.split("\\"):
        raise ValueError("Path traversal not allowed")

    base = (get_artifacts_root() / run_id).resolve()
    target = (base / rel_path).resolve()

    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError("Invalid artifact path")

    return target


async def get_evidence(run_id: str) -> dict[str, Any]:
    """获取 evidence.json 内容"""
    try:
        uuid_run_id = UUID(run_id)
    except ValueError:
        return {"error": "Invalid run_id format"}

    evidence = load_evidence(uuid_run_id)
    if evidence is None:
        return {"error": "Evidence not found", "run_id": run_id}

    return evidence.model_dump(mode="json")


async def list_artifacts(run_id: str) -> dict[str, Any]:
    """列出运行目录下的所有产物"""
    try:
        uuid_run_id = UUID(run_id)
    except ValueError:
        return {"error": "Invalid run_id format"}

    run_dir = get_artifacts_root() / str(uuid_run_id)
    if not run_dir.exists():
        return {"error": "Run directory not found", "run_id": run_id}

    artifacts = []
    for path in run_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(run_dir)
            artifacts.append({
                "path": str(rel),
                "size": path.stat().st_size,
            })

    return {"run_id": run_id, "artifacts": artifacts, "count": len(artifacts)}


async def get_artifact_content(run_id: str, rel_path: str) -> dict[str, Any]:
    """获取产物文件内容（仅文本）"""
    try:
        target = _validate_path(run_id, rel_path)
    except ValueError as e:
        return {"error": str(e)}

    if not target.exists():
        return {"error": "Artifact not found", "path": rel_path}

    if not target.is_file():
        return {"error": "Path is not a file", "path": rel_path}

    # 只允许文本文件
    text_suffixes = {".json", ".xml", ".txt", ".log", ".html", ".md", ".yaml", ".yml"}
    if target.suffix.lower() not in text_suffixes:
        return {"error": "Binary files not supported", "path": rel_path}

    try:
        content = target.read_text(encoding="utf-8")
        # 限制内容大小
        max_size = 100_000
        if len(content) > max_size:
            content = content[:max_size] + f"\n... (truncated, total {len(content)} chars)"
        return {"path": rel_path, "content": content}
    except UnicodeDecodeError:
        return {"error": "Failed to decode file as UTF-8", "path": rel_path}


# 工具函数映射
TOOL_HANDLERS = {
    "get_evidence": get_evidence,
    "list_artifacts": list_artifacts,
    "get_artifact_content": get_artifact_content,
}
