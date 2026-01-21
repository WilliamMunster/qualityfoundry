"""QualityFoundry - Diff Reporter

对比 baseline 与 current 结果，生成 diff 报告。
"""

from __future__ import annotations

from qualityfoundry.governance.evals.models import (
    BaselineData,
    CaseResult,
    DiffItem,
    DiffReport,
)


def generate_diff(
    baseline: BaselineData,
    current_results: list[CaseResult],
    current_git_sha: str | None = None,
) -> DiffReport:
    """生成 diff 报告

    Args:
        baseline: 基线数据
        current_results: 当前运行结果
        current_git_sha: 当前 git sha

    Returns:
        Diff 报告
    """
    # 按 case_id 建立索引
    baseline_map = {r.case_id: r for r in baseline.results}
    current_map = {r.case_id: r for r in current_results}

    all_case_ids = set(baseline_map.keys()) | set(current_map.keys())
    diffs: list[DiffItem] = []
    passed = 0
    regressions = 0
    improvements = 0
    added = 0
    removed = 0

    for case_id in sorted(all_case_ids):
        base = baseline_map.get(case_id)
        curr = current_map.get(case_id)

        if not base:
            # 新增的 case
            added += 1
            diffs.append(DiffItem(
                case_id=case_id,
                status="ADDED",
                expected_decision=curr.expected_decision if curr else None,
                current_decision=curr.actual_decision if curr else None,
                current_evidence=curr.evidence_path if curr else None,
            ))
        elif not curr:
            # 移除的 case
            removed += 1
            diffs.append(DiffItem(
                case_id=case_id,
                status="REMOVED",
                expected_decision=base.expected_decision,
                baseline_decision=base.actual_decision,
                baseline_evidence=base.evidence_path,
            ))
        elif base.actual_decision != curr.actual_decision:
            # Decision 变化
            if curr.passed and not base.passed:
                # 改进：之前失败，现在通过
                improvements += 1
                diffs.append(DiffItem(
                    case_id=case_id,
                    status="IMPROVED",
                    expected_decision=curr.expected_decision,
                    baseline_decision=base.actual_decision,
                    current_decision=curr.actual_decision,
                    baseline_evidence=base.evidence_path,
                    current_evidence=curr.evidence_path,
                ))
            elif not curr.passed and base.passed:
                # 回归：之前通过，现在失败
                regressions += 1
                diffs.append(DiffItem(
                    case_id=case_id,
                    status="REGRESSION",
                    expected_decision=curr.expected_decision,
                    baseline_decision=base.actual_decision,
                    current_decision=curr.actual_decision,
                    baseline_evidence=base.evidence_path,
                    current_evidence=curr.evidence_path,
                ))
            else:
                # Decision 变化但 passed 状态未变（边缘情况）
                diffs.append(DiffItem(
                    case_id=case_id,
                    status="CHANGED",
                    expected_decision=curr.expected_decision,
                    baseline_decision=base.actual_decision,
                    current_decision=curr.actual_decision,
                    baseline_evidence=base.evidence_path,
                    current_evidence=curr.evidence_path,
                ))
        else:
            # 无变化
            passed += 1

    return DiffReport(
        baseline_id=baseline.baseline_id,
        baseline_git_sha=baseline.git_sha,
        current_git_sha=current_git_sha,
        total_cases=len(all_case_ids),
        passed=passed,
        regressions=regressions,
        improvements=improvements,
        added=added,
        removed=removed,
        diffs=diffs,
    )
