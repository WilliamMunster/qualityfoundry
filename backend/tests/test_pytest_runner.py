"""Tests for run_pytest tool (PR-2)

验证 pytest runner 工具的正确性。
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from qualityfoundry.tools.contracts import ArtifactType, ToolRequest, ToolStatus
from qualityfoundry.tools.runners.pytest_runner import (
    _is_safe_test_path,
    _parse_junit_stats,
    run_pytest,
)


class TestSafeTestPath:
    """路径安全验证测试"""

    def test_valid_tests_directory(self):
        assert _is_safe_test_path("tests/") is True
        assert _is_safe_test_path("tests") is True
        assert _is_safe_test_path("tests/unit") is True
        assert _is_safe_test_path("tests/unit/test_foo.py") is True

    def test_valid_test_directory(self):
        assert _is_safe_test_path("test/") is True
        assert _is_safe_test_path("test") is True

    def test_valid_single_file(self):
        assert _is_safe_test_path("test_sample.py") is True

    def test_invalid_path_traversal(self):
        assert _is_safe_test_path("../tests") is False
        assert _is_safe_test_path("tests/../../../etc/passwd") is False
        assert _is_safe_test_path("..") is False

    def test_invalid_absolute_path(self):
        assert _is_safe_test_path("/etc/passwd") is False
        assert _is_safe_test_path("/tmp/tests/") is False

    def test_invalid_other_directories(self):
        assert _is_safe_test_path("src/") is False
        assert _is_safe_test_path("app/") is False
        assert _is_safe_test_path("random_file.py") is False


class TestParseJunitStats:
    """JUnit XML 解析测试"""

    def test_parse_valid_junit(self):
        """解析有效的 JUnit XML"""
        junit_content = '''<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="pytest" errors="1" failures="2" skipped="1" tests="10" time="1.234">
    </testsuite>
</testsuites>'''

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w") as f:
            f.write(junit_content)
            f.flush()
            path = Path(f.name)

        stats = _parse_junit_stats(path)

        assert stats["tests"] == 10
        assert stats["failures"] == 2
        assert stats["errors"] == 1
        assert stats["skipped"] == 1
        assert abs(stats["time"] - 1.234) < 0.001

        path.unlink()

    def test_parse_empty_file(self):
        """解析空文件"""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w") as f:
            f.write("")
            f.flush()
            path = Path(f.name)

        stats = _parse_junit_stats(path)
        assert stats == {}

        path.unlink()

    def test_parse_nonexistent_file(self):
        """解析不存在的文件"""
        stats = _parse_junit_stats(Path("/nonexistent/junit.xml"))
        assert stats == {}


class TestRunPytest:
    """run_pytest 工具测试"""

    @pytest.mark.asyncio
    async def test_missing_test_path(self):
        """缺少必填参数"""
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={},
        )

        result = await run_pytest(request)

        assert result.status == ToolStatus.FAILED
        assert "test_path" in result.error_message

    @pytest.mark.asyncio
    async def test_invalid_test_path(self):
        """无效的测试路径"""
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={"test_path": "../../../etc/passwd"},
        )

        result = await run_pytest(request)

        assert result.status == ToolStatus.FAILED
        assert "Invalid test_path" in result.error_message

    @pytest.mark.asyncio
    async def test_run_sample_tests_pass(self):
        """运行通过的测试"""
        # 使用 fixtures 中的测试文件
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={
                "test_path": "tests/fixtures/sample_tests/test_sample.py",
            },
        )

        result = await run_pytest(request)

        assert result.status == ToolStatus.SUCCESS
        assert result.metrics.exit_code == 0
        assert result.metrics.steps_total == 4  # 4 个测试
        assert result.metrics.steps_failed == 0

        # 检查 JUnit XML artifact
        junit_artifacts = [a for a in result.artifacts if a.type == ArtifactType.JUNIT_XML]
        assert len(junit_artifacts) == 1
        assert "junit.xml" in junit_artifacts[0].path

    @pytest.mark.asyncio
    async def test_run_sample_tests_fail(self):
        """运行包含失败的测试"""
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={
                "test_path": "tests/fixtures/sample_tests/test_with_failure.py",
            },
        )

        result = await run_pytest(request)

        assert result.status == ToolStatus.FAILED
        assert result.metrics.exit_code != 0
        assert result.metrics.steps_total == 3  # 3 个测试
        assert result.metrics.steps_failed == 1  # 1 个失败

        # 即使失败也应该有 JUnit XML
        junit_artifacts = [a for a in result.artifacts if a.type == ArtifactType.JUNIT_XML]
        assert len(junit_artifacts) == 1

    @pytest.mark.asyncio
    async def test_run_with_extra_args(self):
        """使用额外参数"""
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={
                "test_path": "tests/fixtures/sample_tests/test_sample.py",
                "extra_args": ["-v", "--tb=short"],
            },
        )

        result = await run_pytest(request)

        assert result.status == ToolStatus.SUCCESS
        # -v 应该产生更详细的输出
        assert result.stdout is not None

    @pytest.mark.asyncio
    async def test_run_nonexistent_path(self):
        """运行不存在的测试路径"""
        request = ToolRequest(
            tool_name="run_pytest",
            run_id=uuid4(),
            args={
                "test_path": "tests/nonexistent_test_file.py",
            },
        )

        result = await run_pytest(request)

        # pytest 会返回非零退出码
        assert result.status == ToolStatus.FAILED
        assert result.metrics.exit_code != 0
