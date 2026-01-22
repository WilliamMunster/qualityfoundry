"""QualityFoundry - Tool Contracts (统一工具契约)

定义所有工具的标准化输入/输出结构，是后续所有工具实现的"地基"。

设计原则：
1. 统一性：所有工具使用相同的 Request/Result 结构
2. 可追溯：每个结果都包含时间戳、产物引用、指标
3. 兼容性：可与现有 ExecutionResponse/StepEvidence 互转
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ArtifactType(str, Enum):
    """产物类型"""
    SCREENSHOT = "screenshot"
    JUNIT_XML = "junit_xml"
    TRACE = "trace"
    LOG = "log"
    REPORT = "report"
    VIDEO = "video"
    HAR = "har"
    OTHER = "other"


class ArtifactRef(BaseModel):
    """产物引用：描述工具执行产生的文件/资源

    用于追溯和证据链构建。
    """
    model_config = ConfigDict(extra="forbid")

    type: ArtifactType = Field(..., description="产物类型")
    path: str = Field(..., description="产物路径（相对于 artifact_dir 或绝对路径）")
    mime: str = Field(default="application/octet-stream", description="MIME 类型")
    size: int = Field(default=0, description="文件大小（字节）")
    sha256: str | None = Field(default=None, description="SHA256 校验和（可选）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    @classmethod
    def from_file(
        cls,
        path: Path | str,
        artifact_type: ArtifactType,
        mime: str | None = None,
        compute_hash: bool = False,
    ) -> "ArtifactRef":
        """从文件创建 ArtifactRef"""
        p = Path(path)
        if not p.exists():
            return cls(type=artifact_type, path=str(path), mime=mime or "application/octet-stream")

        size = p.stat().st_size
        sha256 = None
        if compute_hash:
            sha256 = hashlib.sha256(p.read_bytes()).hexdigest()

        # 根据后缀推断 MIME
        if mime is None:
            mime = _guess_mime(p)

        return cls(type=artifact_type, path=str(path), mime=mime, size=size, sha256=sha256)


def _guess_mime(path: Path) -> str:
    """根据文件后缀推断 MIME 类型"""
    suffix_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".xml": "application/xml",
        ".json": "application/json",
        ".html": "text/html",
        ".txt": "text/plain",
        ".log": "text/plain",
        ".zip": "application/zip",
        ".har": "application/json",
        ".webm": "video/webm",
        ".mp4": "video/mp4",
    }
    return suffix_map.get(path.suffix.lower(), "application/octet-stream")


class ToolStatus(str, Enum):
    """工具执行状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ToolMetrics(BaseModel):
    """工具执行指标

    用于性能分析、成本计算和监控告警。
    """
    model_config = ConfigDict(extra="allow")

    duration_ms: int = Field(default=0, description="执行耗时（毫秒）")
    exit_code: int | None = Field(default=None, description="进程退出码（如适用）")
    steps_total: int = Field(default=0, description="总步骤数")
    steps_passed: int = Field(default=0, description="成功步骤数")
    steps_failed: int = Field(default=0, description="失败步骤数")
    retries: int = Field(default=0, description="重试次数")
    # Cost governance fields (Phase 5.1)
    attempts: int = Field(default=1, ge=1, description="总尝试次数（1 + retries_used）")
    retries_used: int = Field(default=0, ge=0, description="实际使用的重试次数")
    timed_out: bool = Field(default=False, description="是否因超时终止")


class ToolRequest(BaseModel):
    """统一工具请求

    所有工具的输入都通过此结构标准化。
    """
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., description="工具名称（如 run_playwright, run_pytest）")
    args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    run_id: UUID = Field(..., description="执行运行 ID（用于关联和追溯）")
    timeout_s: int = Field(default=120, ge=1, le=3600, description="超时时间（秒）")
    max_retries: int = Field(default=0, ge=0, le=10, description="最大重试次数")
    dry_run: bool = Field(default=False, description="是否为演练模式（不实际执行）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class ToolResult(BaseModel):
    """统一工具结果

    所有工具的输出都通过此结构标准化，支持：
    - 状态追踪
    - 标准输出/错误捕获
    - 产物引用
    - 执行指标
    - 时间戳记录
    """
    model_config = ConfigDict(extra="forbid")

    status: ToolStatus = Field(..., description="执行状态")
    stdout: str | None = Field(default=None, description="标准输出")
    stderr: str | None = Field(default=None, description="标准错误")
    error_message: str | None = Field(default=None, description="错误消息（如失败）")
    artifacts: list[ArtifactRef] = Field(default_factory=list, description="产物列表")
    metrics: ToolMetrics = Field(default_factory=ToolMetrics, description="执行指标")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="开始时间")
    ended_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="结束时间")
    artifact_dir: str | None = Field(default=None, description="产物目录路径")
    raw_output: dict[str, Any] | None = Field(default=None, description="原始输出（工具特定）")

    @field_serializer("started_at", "ended_at")
    def serialize_dt(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @property
    def ok(self) -> bool:
        """是否成功"""
        return self.status == ToolStatus.SUCCESS

    @property
    def duration_ms(self) -> int:
        """执行耗时（毫秒）"""
        return self.metrics.duration_ms

    def to_json_log(self) -> dict[str, Any]:
        """转换为结构化 JSON 日志格式"""
        return {
            "status": self.status.value,
            "ok": self.ok,
            "duration_ms": self.duration_ms,
            "artifacts_count": len(self.artifacts),
            "started_at": self.serialize_dt(self.started_at, None),
            "ended_at": self.serialize_dt(self.ended_at, None),
            "error": self.error_message,
        }

    @classmethod
    def success(
        cls,
        artifacts: list[ArtifactRef] | None = None,
        metrics: ToolMetrics | None = None,
        stdout: str | None = None,
        artifact_dir: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        raw_output: dict[str, Any] | None = None,
    ) -> "ToolResult":
        """创建成功结果的便捷方法"""
        now = datetime.now(timezone.utc)
        return cls(
            status=ToolStatus.SUCCESS,
            artifacts=artifacts or [],
            metrics=metrics or ToolMetrics(),
            stdout=stdout,
            artifact_dir=artifact_dir,
            started_at=started_at or now,
            ended_at=ended_at or now,
            raw_output=raw_output,
        )

    @classmethod
    def failed(
        cls,
        error_message: str,
        artifacts: list[ArtifactRef] | None = None,
        metrics: ToolMetrics | None = None,
        stderr: str | None = None,
        artifact_dir: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> "ToolResult":
        """创建失败结果的便捷方法"""
        now = datetime.now(timezone.utc)
        return cls(
            status=ToolStatus.FAILED,
            error_message=error_message,
            artifacts=artifacts or [],
            metrics=metrics or ToolMetrics(),
            stderr=stderr,
            artifact_dir=artifact_dir,
            started_at=started_at or now,
            ended_at=ended_at or now,
        )

    @classmethod
    def timeout(
        cls,
        error_message: str = "Execution timed out",
        artifacts: list[ArtifactRef] | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> "ToolResult":
        """创建超时结果的便捷方法"""
        now = datetime.now(timezone.utc)
        return cls(
            status=ToolStatus.TIMEOUT,
            error_message=error_message,
            artifacts=artifacts or [],
            started_at=started_at or now,
            ended_at=ended_at or now,
        )
