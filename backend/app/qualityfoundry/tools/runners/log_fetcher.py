"""QualityFoundry - Log Fetcher Tool

获取执行日志，支持按 run_id 查询 AI 执行日志。

使用方式：
    request = ToolRequest(
        tool_name="fetch_logs",
        run_id=uuid4(),
        args={
            "target_run_id": "uuid-string",  # 要查询的 run_id
            "log_type": "ai_execution",      # 可选: ai_execution, tool, all
            "limit": 100,                    # 可选: 最大返回条数
        }
    )
    result = await fetch_logs(request)
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from qualityfoundry.tools.base import ToolExecutionContext, log_tool_result
from qualityfoundry.tools.config import get_artifacts_root
from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolRequest,
    ToolResult,
)

logger = logging.getLogger(__name__)


async def fetch_logs(request: ToolRequest) -> ToolResult:
    """日志获取工具：按 run_id 获取执行日志

    Args:
        request: ToolRequest，args 包含：
            - target_run_id: str - 要查询的 run_id（必填）
            - log_type: str (可选) - 日志类型：ai_execution, tool, all（默认 all）
            - limit: int (可选) - 最大返回条数（默认 100）
            - include_artifacts: bool (可选) - 是否包含 artifact 列表（默认 True）

    Returns:
        ToolResult: 包含日志内容，artifacts 包含 log.jsonl
    """
    async with ToolExecutionContext(request) as ctx:
        try:
            args = request.args

            # 验证必填参数
            target_run_id_str = args.get("target_run_id")
            if not target_run_id_str:
                return ctx.failed("Missing required argument: target_run_id")

            try:
                target_run_id = UUID(target_run_id_str)
            except ValueError:
                return ctx.failed(f"Invalid UUID format: {target_run_id_str}")

            # 解析可选参数
            log_type = args.get("log_type", "all")
            limit = args.get("limit", 100)
            include_artifacts = args.get("include_artifacts", True)

            # 收集日志
            logs: list[dict] = []
            artifacts_found: list[dict] = []

            # 1. 从 artifact 目录收集 tool_result.json
            artifact_root = get_artifacts_root()
            run_artifact_dir = artifact_root / str(target_run_id)

            if run_artifact_dir.exists():
                # 收集所有 tool_result.json
                for tool_dir in (run_artifact_dir / "tools").glob("*"):
                    if tool_dir.is_dir():
                        result_file = tool_dir / "tool_result.json"
                        if result_file.exists():
                            try:
                                content = json.loads(result_file.read_text())
                                logs.append({
                                    "source": "tool_result",
                                    "tool_name": tool_dir.name,
                                    "path": str(result_file),
                                    "content": content,
                                })
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse {result_file}: {e}")

                # 收集 artifacts 列表
                if include_artifacts:
                    for artifact_path in run_artifact_dir.rglob("*"):
                        if artifact_path.is_file() and artifact_path.name != "tool_result.json":
                            artifacts_found.append({
                                "path": str(artifact_path.relative_to(artifact_root)),
                                "name": artifact_path.name,
                                "size": artifact_path.stat().st_size,
                            })

            # 2. 尝试从数据库获取 AI 执行日志（如果可用）
            # 注意：这里不直接导入数据库依赖，以保持工具的独立性
            # 实际集成时可以通过依赖注入或服务层获取
            ai_logs = await _fetch_ai_execution_logs(target_run_id, limit)
            if ai_logs:
                logs.extend(ai_logs)

            # 3. 按类型过滤
            if log_type != "all":
                logs = [log for log in logs if log.get("source") == log_type or log.get("type") == log_type]

            # 4. 限制条数
            logs = logs[:limit]

            # 5. 保存为 artifact
            output_file = ctx.artifact_dir / "logs.jsonl"
            with output_file.open("w", encoding="utf-8") as f:
                for log in logs:
                    f.write(json.dumps(log, ensure_ascii=False, default=str) + "\n")

            log_artifact = ArtifactRef.from_file(output_file, ArtifactType.LOG)
            ctx.add_artifact(log_artifact)

            # 6. 构建结果
            summary = {
                "target_run_id": str(target_run_id),
                "logs_count": len(logs),
                "artifacts_count": len(artifacts_found),
                "log_types": list(set(log.get("source", "unknown") for log in logs)),
            }

            ctx.update_metrics(
                steps_total=len(logs),
                steps_passed=len(logs),
            )

            result = ctx.success(
                stdout=json.dumps(summary, indent=2),
                raw_output={
                    "logs": logs,
                    "artifacts": artifacts_found,
                    "summary": summary,
                },
            )

            log_tool_result(result, "fetch_logs")
            return result

        except Exception as e:
            logger.exception("fetch_logs failed")
            return ctx.failed(error_message=str(e))


async def _fetch_ai_execution_logs(run_id: UUID, limit: int) -> list[dict]:
    """从数据库获取 AI 执行日志

    注意：这是一个简化实现，实际集成时应通过服务层获取。
    """
    # TODO: 在 PR-3/PR-4 中实现与数据库的集成
    # 目前只返回空列表，因为我们还没有与现有 AIExecutionLog 模型集成
    return []


# 工具元数据（用于注册）
TOOL_METADATA = {
    "name": "fetch_logs",
    "description": "Fetch execution logs by run_id",
    "version": "1.0.0",
    "tags": ["logs", "debugging", "evidence"],
}
