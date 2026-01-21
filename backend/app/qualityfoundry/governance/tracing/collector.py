"""QualityFoundry - Trace Collector (证据收集器)

将执行结果汇总为 evidence.json，作为证据链的单一事实来源。

Evidence 结构:
{
  "run_id": "uuid",
  "input_nl": "自然语言输入",
  "environment": {"base_url": "...", "headless": true},
  "tool_calls": [
    {"tool_name": "run_pytest", "status": "success", "duration_ms": 1234, "exit_code": 0}
  ],
  "artifacts": [
    {"type": "junit_xml", "path": "run_id/tools/run_pytest/junit.xml", ...}
  ],
  "summary": {"tests": 5, "failures": 0, "errors": 0, "skipped": 0, "time": 2.34},
  "collected_at": "2024-01-01T00:00:00Z"
}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from qualityfoundry.governance.repro import ReproMeta, get_repro_meta
from qualityfoundry.governance.tracing.junit_parser import JUnitSummary, parse_junit_xml
from qualityfoundry.tools.base import make_relative_path
from qualityfoundry.tools.config import get_artifacts_root
from qualityfoundry.tools.contracts import ArtifactType, ToolResult

logger = logging.getLogger(__name__)


class ToolCallSummary(BaseModel):
    """工具调用摘要（只保留关键字段，不存储大文本）"""
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: str
    duration_ms: int = 0
    exit_code: int | None = None
    steps_total: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    error_message: str | None = None

    @classmethod
    def from_tool_result(cls, result: ToolResult, tool_name: str) -> "ToolCallSummary":
        """从 ToolResult 创建摘要"""
        return cls(
            tool_name=tool_name,
            status=result.status.value,
            duration_ms=result.metrics.duration_ms,
            exit_code=result.metrics.exit_code,
            steps_total=result.metrics.steps_total,
            steps_passed=result.metrics.steps_passed,
            steps_failed=result.metrics.steps_failed,
            error_message=result.error_message[:200] if result.error_message else None,
        )


class EvidenceSummary(BaseModel):
    """证据摘要（测试统计）"""
    model_config = ConfigDict(extra="allow")

    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    time: float = 0.0
    passed: int = 0  # 计算字段

    @classmethod
    def from_junit(cls, junit: JUnitSummary) -> "EvidenceSummary":
        """从 JUnit 摘要创建"""
        passed = junit["tests"] - junit["failures"] - junit["errors"] - junit["skipped"]
        return cls(
            tests=junit["tests"],
            failures=junit["failures"],
            errors=junit["errors"],
            skipped=junit["skipped"],
            time=junit["time"],
            passed=max(0, passed),
        )

    @classmethod
    def from_tool_results(cls, results: list[ToolResult]) -> "EvidenceSummary":
        """从 ToolResult 列表聚合（当没有 JUnit 时）"""
        total_steps = sum(r.metrics.steps_total for r in results)
        passed_steps = sum(r.metrics.steps_passed for r in results)
        failed_steps = sum(r.metrics.steps_failed for r in results)
        total_time = sum(r.metrics.duration_ms for r in results) / 1000.0

        return cls(
            tests=total_steps,
            failures=failed_steps,
            errors=0,
            skipped=0,
            time=total_time,
            passed=passed_steps,
        )


class Evidence(BaseModel):
    """完整证据结构"""
    model_config = ConfigDict(extra="forbid")

    run_id: str
    input_nl: str
    environment: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallSummary] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    summary: EvidenceSummary | None = None
    repro: ReproMeta | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_dump_json_for_file(self) -> str:
        """导出为 JSON 字符串（用于写文件）"""
        data = self.model_dump(mode="json")
        # 格式化 collected_at
        if isinstance(data.get("collected_at"), str):
            pass  # 已经是字符串
        elif data.get("collected_at"):
            data["collected_at"] = data["collected_at"].isoformat()
        return json.dumps(data, indent=2, ensure_ascii=False)


class TraceCollector:
    """证据收集器

    将执行结果汇总为 evidence.json。

    Usage:
        collector = TraceCollector(run_id, input_nl, environment)
        collector.add_tool_result("run_pytest", result)
        evidence = collector.collect()
        evidence_path = collector.save()
    """

    def __init__(
        self,
        run_id: UUID | str,
        input_nl: str,
        environment: dict[str, Any] | None = None,
        artifact_root: Path | None = None,
    ):
        self.run_id = str(run_id)
        self.input_nl = input_nl
        self.environment = environment or {}
        self.artifact_root = artifact_root or get_artifacts_root()
        self._tool_results: list[tuple[str, ToolResult]] = []

    def add_tool_result(self, tool_name: str, result: ToolResult) -> None:
        """添加工具执行结果"""
        self._tool_results.append((tool_name, result))

    def add_tool_results(self, results: list[tuple[str, ToolResult]]) -> None:
        """批量添加工具执行结果"""
        self._tool_results.extend(results)

    def collect(self) -> Evidence:
        """收集并生成 Evidence 对象"""
        # 1. 提取 tool_calls 摘要
        tool_calls = [
            ToolCallSummary.from_tool_result(result, name)
            for name, result in self._tool_results
        ]

        # 2. 收集所有 artifacts（转为相对路径）
        all_artifacts: list[dict[str, Any]] = []
        junit_artifacts: list[Path] = []

        for _, result in self._tool_results:
            for artifact in result.artifacts:
                # 转换为相对路径
                rel_path = make_relative_path(Path(artifact.path), self.artifact_root)
                artifact_data = artifact.model_dump(mode="json")
                artifact_data["path"] = rel_path
                all_artifacts.append(artifact_data)

                # 记录 JUnit XML 用于后续解析
                if artifact.type == ArtifactType.JUNIT_XML:
                    junit_artifacts.append(Path(artifact.path))

        # 3. 生成 summary
        summary = self._generate_summary(junit_artifacts)

        # 4. 收集可复现性元数据
        repro = get_repro_meta(self.artifact_root.parent if self.artifact_root else None)

        # 5. 构建 Evidence
        return Evidence(
            run_id=self.run_id,
            input_nl=self.input_nl,
            environment=self.environment,
            tool_calls=tool_calls,
            artifacts=all_artifacts,
            summary=summary,
            repro=repro,
        )

    def _generate_summary(self, junit_paths: list[Path]) -> EvidenceSummary:
        """生成测试摘要

        优先从 JUnit XML 解析；没有 JUnit 时从 ToolResult 聚合。
        """
        # 尝试从 JUnit XML 获取
        for junit_path in junit_paths:
            if junit_path.exists():
                junit_summary = parse_junit_xml(junit_path)
                if junit_summary["tests"] > 0:
                    return EvidenceSummary.from_junit(junit_summary)

        # Fallback: 从 ToolResult 聚合
        results = [r for _, r in self._tool_results]
        return EvidenceSummary.from_tool_results(results)

    def save(self, evidence: Evidence | None = None) -> Path:
        """保存 evidence.json 到 artifact 目录

        Args:
            evidence: Evidence 对象（如果为 None，会调用 collect()）

        Returns:
            evidence.json 的路径
        """
        if evidence is None:
            evidence = self.collect()

        # 确定保存路径
        run_dir = self.artifact_root / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = run_dir / "evidence.json"

        # 写入文件
        evidence_path.write_text(evidence.model_dump_json_for_file(), encoding="utf-8")
        logger.info(f"Evidence saved to {evidence_path}")

        return evidence_path

    def collect_and_save(self) -> tuple[Evidence, Path]:
        """收集并保存（便捷方法）"""
        evidence = self.collect()
        path = self.save(evidence)
        return evidence, path


def load_evidence(run_id: UUID | str, artifact_root: Path | None = None) -> Evidence | None:
    """加载已保存的 evidence.json

    Args:
        run_id: 运行 ID
        artifact_root: artifact 根目录

    Returns:
        Evidence 对象，如果不存在返回 None
    """
    root = artifact_root or get_artifacts_root()
    evidence_path = root / str(run_id) / "evidence.json"

    if not evidence_path.exists():
        return None

    try:
        data = json.loads(evidence_path.read_text(encoding="utf-8"))
        return Evidence.model_validate(data)
    except Exception as e:
        logger.warning(f"Failed to load evidence from {evidence_path}: {e}")
        return None
