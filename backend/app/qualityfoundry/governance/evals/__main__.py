"""QualityFoundry - Evals CLI

命令行入口：运行回归测试并生成报告。

Usage:
    python -m governance.evals --dataset <path> --output <dir> --baseline-id <id> [--update-baseline]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from qualityfoundry.governance.evals.diff import generate_diff
from qualityfoundry.governance.evals.models import BaselineData, GoldenDataset
from qualityfoundry.governance.evals.runner import run_all_cases
from qualityfoundry.governance.repro import get_repro_meta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run regression tests against Golden Dataset")
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to Golden Dataset YAML file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="Output directory for results (default: results/)",
    )
    parser.add_argument(
        "--baseline-id",
        type=str,
        default="default",
        help="Baseline identifier (default: default)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current results",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 if any regressions are detected (default behavior when baseline exists)",
    )
    args = parser.parse_args()

    # 确保路径
    args.output.mkdir(parents=True, exist_ok=True)
    baseline_dir = args.output / "baselines"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = args.output / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    baseline_path = baseline_dir / f"{args.baseline_id}.json"

    # 加载 dataset
    logger.info(f"Loading dataset from {args.dataset}")
    dataset = GoldenDataset.load(args.dataset)
    logger.info(f"Loaded {len(dataset.cases)} cases")

    # 运行当前测试
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_output = runs_dir / timestamp
    logger.info(f"Running tests, output to {run_output}")
    current_results = run_all_cases(dataset, run_output)

    # 获取当前 repro 信息
    repro = get_repro_meta()

    # 统计结果
    passed_count = sum(1 for r in current_results if r.passed)
    total_count = len(current_results)
    logger.info(f"Results: {passed_count}/{total_count} passed")

    # 检查 baseline
    if not baseline_path.exists() or args.update_baseline:
        # 创建或更新 baseline
        baseline = BaselineData(
            baseline_id=args.baseline_id,
            git_sha=repro.git_sha,
            results=current_results,
        )
        baseline.save(baseline_path)
        logger.info(f"Baseline saved to {baseline_path}")

        if not args.update_baseline:
            logger.info("No existing baseline found. Created new baseline.")
            print(f"\n✅ {passed_count}/{total_count} passed")
            print(f"📁 Baseline created: {baseline_path}")
            return 0
        else:
            print(f"\n✅ Baseline updated: {args.baseline_id}")
            print(f"📁 Saved to: {baseline_path}")
            return 0

    # 加载 baseline 并生成 diff
    logger.info(f"Loading baseline from {baseline_path}")
    baseline = BaselineData.load(baseline_path)

    diff_report = generate_diff(baseline, current_results, repro.git_sha)

    # 保存 diff 报告
    report_path = run_output / "diff_report.md"
    report_path.write_text(diff_report.to_markdown(), encoding="utf-8")
    logger.info(f"Diff report saved to {report_path}")

    # 输出结果
    print(f"\n{'=' * 50}")
    print(f"Regression Results: {args.baseline_id}")
    print(f"{'=' * 50}")
    print(f"Total: {diff_report.total_cases}")
    print(f"Passed: {diff_report.passed}")
    print(f"Regressions: {diff_report.regressions}")
    print(f"Improvements: {diff_report.improvements}")
    print(f"Added: {diff_report.added}")
    print(f"Removed: {diff_report.removed}")
    print(f"\n📁 Report: {report_path}")

    # 返回码：有回归则返回非零
    return 1 if diff_report.regressions > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
