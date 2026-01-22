"""QualityFoundry - Tool Base (统一执行封装)

提供工具执行的通用功能：
- 超时控制
- 日志记录
- Artifact 落盘
- 指标收集
- 敏感数据脱敏
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

from qualityfoundry.tools.config import (
    get_artifacts_root,
    redact_sensitive,
    truncate_output,
)
from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolMetrics,
    ToolRequest,
    ToolResult,
    ToolStatus,
)

logger = logging.getLogger(__name__)


def get_artifact_dir(run_id: UUID, tool_name: str, root: Path | None = None) -> Path:
    """获取工具的 artifact 目录

    结构: {root}/{run_id}/tools/{tool_name}/
    """
    root = root or get_artifacts_root()
    artifact_dir = root / str(run_id) / "tools" / tool_name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def make_relative_path(absolute_path: Path, artifact_root: Path | None = None) -> str:
    """将绝对路径转换为相对于 artifact_root 的路径

    用于 ArtifactRef.path 统一存储相对路径。
    """
    root = artifact_root or get_artifacts_root()
    try:
        return str(absolute_path.relative_to(root))
    except ValueError:
        # 如果不在 root 下，返回原路径
        return str(absolute_path)


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

    自动脱敏敏感字段（password, token, cookie 等）。

    Args:
        artifact_dir: artifact 目录
        result: 工具执行结果
        request: 工具请求（可选）

    Returns:
        日志文件路径
    """
    log_path = artifact_dir / "tool_result.json"

    # 脱敏 request.args
    request_data = None
    if request:
        request_data = request.model_dump(mode="json")
        if "args" in request_data and isinstance(request_data["args"], dict):
            request_data["args"] = redact_sensitive(request_data["args"])

    # 截断过长的 stdout/stderr
    result_data = result.model_dump(mode="json")
    if result_data.get("stdout"):
        result_data["stdout"] = truncate_output(result_data["stdout"])
    if result_data.get("stderr"):
        result_data["stderr"] = truncate_output(result_data["stderr"])

    log_data = {
        "result": result_data,
        "request": request_data,
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
        self.artifact_root = artifact_root or get_artifacts_root()
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


async def execute_with_governance(
    tool_func,
    request: ToolRequest,
    *,
    retryable_statuses: frozenset[ToolStatus] | None = None,
) -> ToolResult:
    """Execute tool with cost governance (timeout + retry enforcement).

    This is the primary entry point for governed tool execution.
    It enforces:
    - timeout_s: Hard timeout per attempt
    - max_retries: Maximum retry attempts on failure/timeout

    Args:
        tool_func: Async tool function that takes ToolRequest and returns ToolResult
        request: Tool request with governance parameters
        retryable_statuses: Statuses that trigger retry (default: FAILED, TIMEOUT)

    Returns:
        ToolResult with governance metrics populated:
        - metrics.attempts: Total attempts made (1 + retries_used)
        - metrics.retries_used: Number of retries actually used
        - metrics.timed_out: Whether final result was due to timeout
        - metrics.duration_ms: Total elapsed time across all attempts
    """
    if retryable_statuses is None:
        retryable_statuses = frozenset({ToolStatus.FAILED, ToolStatus.TIMEOUT})

    max_retries = request.max_retries
    timeout_s = request.timeout_s
    attempts = 0
    retries_used = 0
    total_start_ns = time.perf_counter_ns()
    last_result: ToolResult | None = None

    while attempts <= max_retries:
        attempts += 1
        logger.info(
            f"Governance: executing {request.tool_name} "
            f"(attempt {attempts}/{max_retries + 1}, timeout={timeout_s}s)"
        )

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                tool_func(request),
                timeout=timeout_s,
            )
            last_result = result

            # Success - no retry needed
            if result.status == ToolStatus.SUCCESS:
                break

            # Check if we should retry
            if result.status in retryable_statuses and attempts <= max_retries:
                retries_used += 1
                logger.warning(
                    f"Governance: {request.tool_name} {result.status.value}, "
                    f"retrying ({retries_used}/{max_retries})"
                )
                continue
            else:
                break

        except asyncio.TimeoutError:
            # Create timeout result
            total_elapsed_ms = int((time.perf_counter_ns() - total_start_ns) / 1_000_000)
            last_result = ToolResult(
                status=ToolStatus.TIMEOUT,
                error_message=f"Governance timeout after {timeout_s}s (attempt {attempts})",
                metrics=ToolMetrics(
                    duration_ms=total_elapsed_ms,
                    timed_out=True,
                ),
            )
            logger.warning(
                f"Governance: {request.tool_name} timed out after {timeout_s}s"
            )

            # Check if we should retry timeout
            if ToolStatus.TIMEOUT in retryable_statuses and attempts <= max_retries:
                retries_used += 1
                logger.warning(
                    f"Governance: retrying after timeout ({retries_used}/{max_retries})"
                )
                continue
            else:
                break

        except Exception as e:
            # Unexpected error
            total_elapsed_ms = int((time.perf_counter_ns() - total_start_ns) / 1_000_000)
            last_result = ToolResult(
                status=ToolStatus.FAILED,
                error_message=f"Governance execution error: {e}",
                metrics=ToolMetrics(duration_ms=total_elapsed_ms),
            )
            logger.exception(f"Governance: {request.tool_name} unexpected error")
            break

    # Finalize metrics
    total_elapsed_ms = int((time.perf_counter_ns() - total_start_ns) / 1_000_000)

    if last_result is None:
        # Should not happen, but defensive
        last_result = ToolResult(
            status=ToolStatus.FAILED,
            error_message="No result from tool execution",
            metrics=ToolMetrics(duration_ms=total_elapsed_ms),
        )

    # Update governance metrics
    last_result.metrics.attempts = attempts
    last_result.metrics.retries_used = retries_used
    last_result.metrics.duration_ms = total_elapsed_ms
    if last_result.status == ToolStatus.TIMEOUT:
        last_result.metrics.timed_out = True

    logger.info(
        f"Governance: {request.tool_name} completed - "
        f"status={last_result.status.value}, attempts={attempts}, "
        f"retries_used={retries_used}, duration_ms={total_elapsed_ms}"
    )

    return last_result
