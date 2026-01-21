"""QualityFoundry - Evals Data Models

Golden Dataset 和回归测试的数据模型。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ExpectedResult(BaseModel):
    """期望结果"""
    decision: str
    summary: Optional[dict[str, Any]] = None


class GoldenCase(BaseModel):
    """Golden Dataset 测试用例"""
    id: str
    input_nl: str
    options: dict[str, Any] = Field(default_factory=dict)
    expected: ExpectedResult


class GoldenDataset(BaseModel):
    """Golden Dataset"""
    version: str = "1.0"
    description: str = ""
    cases: list[GoldenCase] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "GoldenDataset":
        """从 YAML 文件加载 dataset"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


class CaseResult(BaseModel):
    """单个用例的执行结果"""
    case_id: str
    run_id: str
    actual_decision: str
    expected_decision: str
    passed: bool
    policy_hash: Optional[str] = None
    git_sha: Optional[str] = None
    evidence_path: str
    error_message: Optional[str] = None


class BaselineData(BaseModel):
    """基线数据"""
    baseline_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    git_sha: Optional[str] = None
    results: list[CaseResult] = Field(default_factory=list)

    def save(self, path: Path) -> None:
        """保存基线到文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "BaselineData":
        """从文件加载基线"""
        with open(path, "r", encoding="utf-8") as f:
            return cls.model_validate_json(f.read())


class DiffItem(BaseModel):
    """单个 diff 项"""
    case_id: str
    status: str  # CHANGED, ADDED, REMOVED
    expected_decision: Optional[str] = None
    baseline_decision: Optional[str] = None
    current_decision: Optional[str] = None
    baseline_evidence: Optional[str] = None
    current_evidence: Optional[str] = None


class DiffReport(BaseModel):
    """Diff 报告"""
    baseline_id: str
    baseline_git_sha: Optional[str] = None
    current_git_sha: Optional[str] = None
    total_cases: int = 0
    passed: int = 0
    regressions: int = 0
    improvements: int = 0
    added: int = 0
    removed: int = 0
    diffs: list[DiffItem] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        lines = [
            "# Regression Report",
            "",
            "## Summary",
            f"- **Baseline**: `{self.baseline_id}` (`{self.baseline_git_sha or 'unknown'}`)",
            f"- **Current**: `{self.current_git_sha or 'unknown'}`",
            f"- **Total Cases**: {self.total_cases}",
            f"- **Passed**: {self.passed}",
            f"- **Regressions**: {self.regressions}",
            f"- **Improvements**: {self.improvements}",
            "",
        ]

        if self.diffs:
            lines.append("## Changes")
            lines.append("")
            lines.append("| Case ID | Status | Expected | Baseline | Current |")
            lines.append("|---------|--------|----------|----------|---------|")
            for diff in self.diffs:
                lines.append(
                    f"| {diff.case_id} | {diff.status} | "
                    f"{diff.expected_decision or '-'} | "
                    f"{diff.baseline_decision or '-'} | "
                    f"{diff.current_decision or '-'} |"
                )
        else:
            lines.append("## ✅ No Changes")
            lines.append("")
            lines.append("All cases match the baseline.")

        return "\n".join(lines)
