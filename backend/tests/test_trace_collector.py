"""Tests for Trace Collector (PR-3)

验证证据收集器的正确性。
"""

import json
import tempfile
from pathlib import Path
from uuid import uuid4


from qualityfoundry.governance.tracing.collector import (
    EvidenceSummary,
    ToolCallSummary,
    TraceCollector,
    load_evidence,
)
from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolMetrics,
    ToolResult,
    ToolStatus,
)


class TestToolCallSummary:
    """ToolCallSummary 测试"""

    def test_from_tool_result_success(self):
        """从成功的 ToolResult 创建摘要"""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            metrics=ToolMetrics(
                duration_ms=1234,
                exit_code=0,
                steps_total=5,
                steps_passed=5,
                steps_failed=0,
            ),
        )

        summary = ToolCallSummary.from_tool_result(result, "run_pytest")

        assert summary.tool_name == "run_pytest"
        assert summary.status == "success"
        assert summary.duration_ms == 1234
        assert summary.exit_code == 0
        assert summary.steps_total == 5
        assert summary.steps_passed == 5
        assert summary.error_message is None

    def test_from_tool_result_failed(self):
        """从失败的 ToolResult 创建摘要"""
        result = ToolResult(
            status=ToolStatus.FAILED,
            error_message="Test failed: AssertionError",
            metrics=ToolMetrics(duration_ms=500),
        )

        summary = ToolCallSummary.from_tool_result(result, "run_playwright")

        assert summary.status == "failed"
        assert "AssertionError" in summary.error_message

    def test_truncate_long_error(self):
        """长错误消息被截断"""
        long_error = "x" * 500
        result = ToolResult(
            status=ToolStatus.FAILED,
            error_message=long_error,
        )

        summary = ToolCallSummary.from_tool_result(result, "test")

        assert len(summary.error_message) == 200


class TestEvidenceSummary:
    """EvidenceSummary 测试"""

    def test_from_junit(self):
        """从 JUnit 摘要创建"""
        junit = {"tests": 10, "failures": 2, "errors": 1, "skipped": 1, "time": 1.5}

        summary = EvidenceSummary.from_junit(junit)

        assert summary.tests == 10
        assert summary.failures == 2
        assert summary.errors == 1
        assert summary.skipped == 1
        assert summary.passed == 6  # 10 - 2 - 1 - 1

    def test_from_tool_results(self):
        """从 ToolResult 列表聚合"""
        results = [
            ToolResult(
                status=ToolStatus.SUCCESS,
                metrics=ToolMetrics(
                    duration_ms=1000,
                    steps_total=5,
                    steps_passed=4,
                    steps_failed=1,
                ),
            ),
            ToolResult(
                status=ToolStatus.SUCCESS,
                metrics=ToolMetrics(
                    duration_ms=500,
                    steps_total=3,
                    steps_passed=3,
                    steps_failed=0,
                ),
            ),
        ]

        summary = EvidenceSummary.from_tool_results(results)

        assert summary.tests == 8  # 5 + 3
        assert summary.passed == 7  # 4 + 3
        assert summary.failures == 1
        assert abs(summary.time - 1.5) < 0.001  # (1000 + 500) / 1000


class TestTraceCollector:
    """TraceCollector 测试"""

    def test_collect_basic(self):
        """基本收集"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_id = uuid4()
            collector = TraceCollector(
                run_id=run_id,
                input_nl="Run tests for login feature",
                environment={"base_url": "http://localhost:3000"},
                artifact_root=Path(tmpdir),
            )

            result = ToolResult(
                status=ToolStatus.SUCCESS,
                metrics=ToolMetrics(
                    duration_ms=1000,
                    steps_total=5,
                    steps_passed=5,
                ),
            )
            collector.add_tool_result("run_pytest", result)

            evidence = collector.collect()

            assert evidence.run_id == str(run_id)
            assert evidence.input_nl == "Run tests for login feature"
            assert evidence.environment["base_url"] == "http://localhost:3000"
            assert len(evidence.tool_calls) == 1
            assert evidence.tool_calls[0].tool_name == "run_pytest"

    def test_collect_with_junit_artifact(self):
        """收集带 JUnit artifact 的结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run_id = uuid4()

            # 创建 JUnit XML
            junit_dir = root / str(run_id) / "tools" / "run_pytest"
            junit_dir.mkdir(parents=True)
            junit_path = junit_dir / "junit.xml"
            junit_path.write_text('''<?xml version="1.0"?>
<testsuite tests="4" failures="0" errors="0" skipped="0" time="0.5"/>''')

            collector = TraceCollector(
                run_id=run_id,
                input_nl="Run tests",
                artifact_root=root,
            )

            result = ToolResult(
                status=ToolStatus.SUCCESS,
                artifacts=[
                    ArtifactRef(
                        type=ArtifactType.JUNIT_XML,
                        path=str(junit_path),
                    )
                ],
            )
            collector.add_tool_result("run_pytest", result)

            evidence = collector.collect()

            assert evidence.summary is not None
            assert evidence.summary.tests == 4
            assert evidence.summary.failures == 0
            assert len(evidence.artifacts) == 1

    def test_save_and_load(self):
        """保存和加载 evidence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run_id = uuid4()

            collector = TraceCollector(
                run_id=run_id,
                input_nl="Test input",
                environment={"headless": True},
                artifact_root=root,
            )

            result = ToolResult(status=ToolStatus.SUCCESS)
            collector.add_tool_result("test_tool", result)

            evidence, path = collector.collect_and_save()

            assert path.exists()
            assert path.name == "evidence.json"

            # 验证文件内容
            content = json.loads(path.read_text())
            assert content["run_id"] == str(run_id)
            assert content["input_nl"] == "Test input"

            # 加载
            loaded = load_evidence(run_id, root)
            assert loaded is not None
            assert loaded.run_id == str(run_id)
            assert loaded.input_nl == "Test input"

    def test_relative_paths(self):
        """artifact 路径转换为相对路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run_id = uuid4()

            collector = TraceCollector(
                run_id=run_id,
                input_nl="Test",
                artifact_root=root,
            )

            # 使用绝对路径
            abs_path = root / str(run_id) / "tools" / "test" / "screenshot.png"
            abs_path.parent.mkdir(parents=True)
            abs_path.write_bytes(b"png")

            result = ToolResult(
                status=ToolStatus.SUCCESS,
                artifacts=[
                    ArtifactRef(
                        type=ArtifactType.SCREENSHOT,
                        path=str(abs_path),
                    )
                ],
            )
            collector.add_tool_result("test", result)

            evidence = collector.collect()

            # 验证路径是相对路径
            artifact_path = evidence.artifacts[0]["path"]
            assert not artifact_path.startswith("/")
            assert str(run_id) in artifact_path

    def test_load_nonexistent(self):
        """加载不存在的 evidence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_evidence(uuid4(), Path(tmpdir))
            assert result is None
