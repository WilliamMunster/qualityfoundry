"""MCP Server Tool Definitions

工具暴露，用于 MCP Server。

Phase 1: run_pytest 作为唯一写工具，受安全链约束。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from qualityfoundry.tools.config import get_artifacts_root
from qualityfoundry.governance.tracing.collector import load_evidence

logger = logging.getLogger(__name__)


# ==================== 工具定义 ====================

# 只读工具（无需认证）
READ_TOOLS = {
    "get_evidence": {
        "description": "获取指定运行的 evidence.json 内容",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "运行 ID (UUID)"}
            },
            "required": ["run_id"],
        },
        "write": False,
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
        "write": False,
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
        "write": False,
    },
}

# 写工具（需要认证 + 安全链）
WRITE_TOOLS = {
    "run_pytest": {
        "description": "执行 pytest 测试（需要认证，受沙箱约束）",
        "parameters": {
            "type": "object",
            "properties": {
                "test_path": {"type": "string", "description": "测试文件或目录路径"},
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "附加 pytest 参数",
                },
            },
            "required": ["test_path"],
        },
        "write": True,
    },
}

# 合并所有工具（向后兼容 SAFE_TOOLS 名称）
SAFE_TOOLS = {**READ_TOOLS, **WRITE_TOOLS}


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


# ==================== 只读工具 Handler ====================


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


# ==================== 写工具 Handler ====================


async def run_pytest_handler(
    test_path: str,
    args: list[str] | None = None,
    *,
    run_id: UUID | None = None,
    sandbox_config: Any = None,
    policy: Any = None,
) -> dict[str, Any]:
    """执行 pytest 测试

    此 handler 由 MCPServer 调用，预期已完成安全检查。

    Args:
        test_path: 测试文件或目录路径
        args: 附加 pytest 参数
        run_id: 运行 ID（由 MCPServer 生成）
        sandbox_config: 沙箱配置（由 MCPServer 从 policy 构建）
        policy: 策略配置

    Returns:
        执行结果
    """
    from qualityfoundry.tools.contracts import ToolRequest, ToolStatus
    from qualityfoundry.tools.registry import get_registry
    from qualityfoundry.tools.runners import register_all_tools

    # 确保工具已注册
    register_all_tools()

    if run_id is None:
        run_id = uuid4()

    # 构建 ToolRequest
    tool_args = {"test_path": test_path}
    if args:
        tool_args["args"] = args

    request = ToolRequest(
        tool_name="run_pytest",
        args=tool_args,
        run_id=run_id,
    )

    # 通过 registry 执行工具（复用现有 sandbox 逻辑）
    registry = get_registry()
    try:
        result = await registry.execute("run_pytest", request, policy=policy)
        return {
            "run_id": str(run_id),
            "status": result.status.value,
            "raw_output": result.raw_output,
            "error": result.error_message,
            "elapsed_ms": result.elapsed_ms,
        }
    except Exception as e:
        logger.exception(f"run_pytest failed: {e}")
        return {
            "run_id": str(run_id),
            "status": ToolStatus.FAILED.value,
            "error": str(e),
        }


# ==================== Handler 映射 ====================

# 只读 handlers（不需要额外参数）
READ_HANDLERS = {
    "get_evidence": get_evidence,
    "list_artifacts": list_artifacts,
    "get_artifact_content": get_artifact_content,
}

# 写 handlers（需要 run_id, sandbox_config, policy）
WRITE_HANDLERS = {
    "run_pytest": run_pytest_handler,
}

# 合并（向后兼容）
TOOL_HANDLERS = {**READ_HANDLERS, **WRITE_HANDLERS}


def is_write_tool(tool_name: str) -> bool:
    """检查工具是否为写工具"""
    return tool_name in WRITE_TOOLS
