"""QualityFoundry - Tool Base (统一执行封装)

提供工具执行的通用功能：
- 超时控制
- 日志记录
- Artifact 落盘
- 指标收集
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolMetrics,
    ToolRequest,
    ToolResult,
    ToolStatus,
)

logger = logging.getLogger(__name__)

# 默认 artifact 根目录
DEFAULT_ARTIFACT_ROOT = Path("artifacts")


def get_artifact_dir(run_id: UUID, tool_name: str, root: Path | None = None) -> Path:
    """获取工具的 artifact 目录

    结构: {root}/{run_id}/tools/{tool_name}/
    """
    root = root or DEFAULT_ARTIFACT_ROOT
    artifact_dir = root / str(run_id) / "tools" / tool_name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def collect_artifacts(
    artifact_dir: Path,
    patterns: list[str] | None = None,
    compute_hash: bool = False,
) -> list[ArtifactRef]:
    """收集目录中的 artifact 文件

    Args:
        artifact_dir: artifact 目录
        patterns: glob 模式列表（默认收集所有文件）
        compute_hash: 是否计算 SHA256

    Returns:
        ArtifactRef 列表
    """
    if not artifact_dir.exists():
        return []

    patterns = patterns or ["*"]
    artifacts: list[ArtifactRef] = []

    for pattern in patterns:
        for path in artifact_dir.glob(pattern):
            if path.is_file():
                artifact_type = _infer_artifact_type(path)
                ref = ArtifactRef.from_file(path, artifact_type, compute_hash=compute_hash)
                artifacts.append(ref)

    return artifacts


def _infer_artifact_type(path: Path) -> ArtifactType:
    """根据文件后缀推断 artifact 类型"""
    suffix = path.suffix.lower()
    type_map = {
        ".png": ArtifactType.SCREENSHOT,
        ".jpg": ArtifactType.SCREENSHOT,
        ".jpeg": ArtifactType.SCREENSHOT,
        ".gif": ArtifactType.SCREENSHOT,
        ".webp": ArtifactType.SCREENSHOT,
        ".xml": ArtifactType.JUNIT_XML,  # 假设 .xml 是 JUnit
        ".zip": ArtifactType.TRACE,  # trace.zip
        ".log": ArtifactType.LOG,
        ".txt": ArtifactType.LOG,
        ".html": ArtifactType.REPORT,
        ".har": ArtifactType.HAR,
        ".webm": ArtifactType.VIDEO,
        ".mp4": ArtifactType.VIDEO,
    }
    return type_map.get(suffix, ArtifactType.OTHER)


def save_tool_log(
    artifact_dir: Path,
    result: ToolResult,
    request: ToolRequest | None = None,
) -> Path:
    """保存工具执行日志到 artifact 目录

    Args:
        artifact_dir: artifact 目录
        result: 工具执行结果
        request: 工具请求（可选）

    Returns:
        日志文件路径
    """
    log_path = artifact_dir / "tool_result.json"
    log_data = {
        "result": result.model_dump(mode="json"),
        "request": request.model_dump(mode="json") if request else None,
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
    return log_path


async def execute_with_timeout(
    coro,
    timeout_s: int,
    *,
    started_at: datetime | None = None,
) -> tuple[Any | None, ToolStatus, str | None]:
    """带超时的异步执行

    Args:
        coro: 协程
        timeout_s: 超时秒数
        started_at: 开始时间（用于错误消息）

    Returns:
        (result, status, error_message)
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_s)
        return result, ToolStatus.SUCCESS, None
    except asyncio.TimeoutError:
        return None, ToolStatus.TIMEOUT, f"Execution timed out after {timeout_s}s"
    except asyncio.CancelledError:
        return None, ToolStatus.CANCELLED, "Execution was cancelled"
    except Exception as e:
        logger.exception("Tool execution failed")
        return None, ToolStatus.FAILED, str(e)


class ToolExecutionContext:
    """工具执行上下文

    提供执行期间的通用功能和状态跟踪。

    Usage:
        async with ToolExecutionContext(request) as ctx:
            # 执行工具逻辑
            ctx.add_artifact(artifact)
            return ctx.success(stdout="done")
    """

    def __init__(
        self,
        request: ToolRequest,
        artifact_root: Path | None = None,
    ):
        self.request = request
        self.artifact_root = artifact_root or DEFAULT_ARTIFACT_ROOT
        self._artifact_dir: Path | None = None
        self._artifacts: list[ArtifactRef] = []
        self._started_at: datetime | None = None
        self._ended_at: datetime | None = None
        self._metrics = ToolMetrics()

    @property
    def artifact_dir(self) -> Path:
        """获取 artifact 目录（惰性创建）"""
        if self._artifact_dir is None:
            self._artifact_dir = get_artifact_dir(
                self.request.run_id,
                self.request.tool_name,
                self.artifact_root,
            )
        return self._artifact_dir

    @property
    def started_at(self) -> datetime:
        return self._started_at or datetime.now(timezone.utc)

    @property
    def ended_at(self) -> datetime:
        return self._ended_at or datetime.now(timezone.utc)

    async def __aenter__(self) -> "ToolExecutionContext":
        self._started_at = datetime.now(timezone.utc)
        self._start_time_ns = time.perf_counter_ns()
        logger.info(
            f"Tool execution started: {self.request.tool_name}, "
            f"run_id={self.request.run_id}"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._ended_at = datetime.now(timezone.utc)
        elapsed_ns = time.perf_counter_ns() - self._start_time_ns
        self._metrics.duration_ms = int(elapsed_ns / 1_000_000)
        logger.info(
            f"Tool execution ended: {self.request.tool_name}, "
            f"duration_ms={self._metrics.duration_ms}"
        )
        return False  # 不抑制异常

    def add_artifact(self, artifact: ArtifactRef) -> None:
        """添加 artifact"""
        self._artifacts.append(artifact)

    def add_artifacts(self, artifacts: list[ArtifactRef]) -> None:
        """批量添加 artifacts"""
        self._artifacts.extend(artifacts)

    def collect_artifacts(
        self,
        patterns: list[str] | None = None,
        compute_hash: bool = False,
    ) -> list[ArtifactRef]:
        """收集 artifact 目录中的文件"""
        collected = collect_artifacts(self.artifact_dir, patterns, compute_hash)
        self._artifacts.extend(collected)
        return collected

    def update_metrics(self, **kwargs) -> None:
        """更新指标"""
        for key, value in kwargs.items():
            if hasattr(self._metrics, key):
                setattr(self._metrics, key, value)

    def success(
        self,
        stdout: str | None = None,
        raw_output: dict[str, Any] | None = None,
    ) -> ToolResult:
        """创建成功结果"""
        return ToolResult(
            status=ToolStatus.SUCCESS,
            stdout=stdout,
            artifacts=self._artifacts,
            metrics=self._metrics,
            started_at=self.started_at,
            ended_at=self.ended_at,
            artifact_dir=str(self.artifact_dir),
            raw_output=raw_output,
        )

    def failed(
        self,
        error_message: str,
        stderr: str | None = None,
    ) -> ToolResult:
        """创建失败结果"""
        return ToolResult(
            status=ToolStatus.FAILED,
            error_message=error_message,
            stderr=stderr,
            artifacts=self._artifacts,
            metrics=self._metrics,
            started_at=self.started_at,
            ended_at=self.ended_at,
            artifact_dir=str(self.artifact_dir),
        )

    def timeout(self, error_message: str | None = None) -> ToolResult:
        """创建超时结果"""
        return ToolResult(
            status=ToolStatus.TIMEOUT,
            error_message=error_message or f"Timed out after {self.request.timeout_s}s",
            artifacts=self._artifacts,
            metrics=self._metrics,
            started_at=self.started_at,
            ended_at=self.ended_at,
            artifact_dir=str(self.artifact_dir),
        )


def log_tool_result(result: ToolResult, tool_name: str) -> None:
    """记录工具结果到日志（结构化 JSON）"""
    log_data = result.to_json_log()
    log_data["tool_name"] = tool_name
    logger.info(f"Tool result: {json.dumps(log_data)}")
