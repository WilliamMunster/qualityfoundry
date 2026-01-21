"""Tests for Tool Base (PR-1)

验证工具执行封装的正确性。
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from qualityfoundry.tools.base import (
    ToolExecutionContext,
    collect_artifacts,
    get_artifact_dir,
)
from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolRequest,
    ToolStatus,
)


class TestGetArtifactDir:
    """get_artifact_dir 测试"""

    def test_creates_directory(self):
        """创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run_id = uuid4()
            tool_name = "my_tool"

            artifact_dir = get_artifact_dir(run_id, tool_name, root)

            assert artifact_dir.exists()
            assert artifact_dir.is_dir()
            assert str(run_id) in str(artifact_dir)
            assert "tools" in str(artifact_dir)
            assert tool_name in str(artifact_dir)

    def test_directory_structure(self):
        """目录结构"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run_id = uuid4()

            artifact_dir = get_artifact_dir(run_id, "test_tool", root)

            expected = root / str(run_id) / "tools" / "test_tool"
            assert artifact_dir == expected


class TestCollectArtifacts:
    """collect_artifacts 测试"""

    def test_collect_all(self):
        """收集所有文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            (artifact_dir / "screenshot.png").write_bytes(b"png")
            (artifact_dir / "junit.xml").write_bytes(b"xml")
            (artifact_dir / "log.txt").write_bytes(b"log")

            artifacts = collect_artifacts(artifact_dir)

            assert len(artifacts) == 3
            types = {a.type for a in artifacts}
            assert ArtifactType.SCREENSHOT in types
            assert ArtifactType.JUNIT_XML in types
            assert ArtifactType.LOG in types

    def test_collect_with_pattern(self):
        """按模式收集"""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            (artifact_dir / "step_001.png").write_bytes(b"png1")
            (artifact_dir / "step_002.png").write_bytes(b"png2")
            (artifact_dir / "junit.xml").write_bytes(b"xml")

            artifacts = collect_artifacts(artifact_dir, patterns=["*.png"])

            assert len(artifacts) == 2
            assert all(a.type == ArtifactType.SCREENSHOT for a in artifacts)

    def test_collect_empty_directory(self):
        """空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            artifacts = collect_artifacts(artifact_dir)
            assert artifacts == []

    def test_collect_nonexistent_directory(self):
        """不存在的目录"""
        artifacts = collect_artifacts(Path("/nonexistent/path"))
        assert artifacts == []


class TestToolExecutionContext:
    """ToolExecutionContext 测试"""

    @pytest.mark.asyncio
    async def test_basic_context(self):
        """基本上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = ToolRequest(
                tool_name="test_tool",
                run_id=uuid4(),
            )

            async with ToolExecutionContext(request, Path(tmpdir)) as ctx:
                assert ctx.artifact_dir.exists()
                result = ctx.success(stdout="done")

            assert result.status == ToolStatus.SUCCESS
            assert result.stdout == "done"
            assert result.metrics.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_add_artifacts(self):
        """添加 artifacts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = ToolRequest(
                tool_name="test_tool",
                run_id=uuid4(),
            )

            async with ToolExecutionContext(request, Path(tmpdir)) as ctx:
                artifact = ArtifactRef(
                    type=ArtifactType.SCREENSHOT,
                    path="/tmp/shot.png",
                )
                ctx.add_artifact(artifact)
                result = ctx.success()

            assert len(result.artifacts) == 1
            assert result.artifacts[0].type == ArtifactType.SCREENSHOT

    @pytest.mark.asyncio
    async def test_failed_result(self):
        """失败结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = ToolRequest(
                tool_name="test_tool",
                run_id=uuid4(),
            )

            async with ToolExecutionContext(request, Path(tmpdir)) as ctx:
                result = ctx.failed("Something went wrong", stderr="Error details")

            assert result.status == ToolStatus.FAILED
            assert result.error_message == "Something went wrong"
            assert result.stderr == "Error details"

    @pytest.mark.asyncio
    async def test_timeout_result(self):
        """超时结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = ToolRequest(
                tool_name="test_tool",
                run_id=uuid4(),
                timeout_s=30,
            )

            async with ToolExecutionContext(request, Path(tmpdir)) as ctx:
                result = ctx.timeout()

            assert result.status == ToolStatus.TIMEOUT
            assert "30s" in result.error_message

    @pytest.mark.asyncio
    async def test_update_metrics(self):
        """更新 metrics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = ToolRequest(
                tool_name="test_tool",
                run_id=uuid4(),
            )

            async with ToolExecutionContext(request, Path(tmpdir)) as ctx:
                ctx.update_metrics(steps_total=5, steps_passed=4, steps_failed=1)
                result = ctx.success()

            assert result.metrics.steps_total == 5
            assert result.metrics.steps_passed == 4
            assert result.metrics.steps_failed == 1

    @pytest.mark.asyncio
    async def test_collect_artifacts_in_context(self):
        """在上下文中收集 artifacts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = ToolRequest(
                tool_name="test_tool",
                run_id=uuid4(),
            )

            async with ToolExecutionContext(request, Path(tmpdir)) as ctx:
                # 创建一些文件
                (ctx.artifact_dir / "shot.png").write_bytes(b"png")
                (ctx.artifact_dir / "result.xml").write_bytes(b"xml")

                # 收集
                collected = ctx.collect_artifacts()
                assert len(collected) == 2

                result = ctx.success()

            assert len(result.artifacts) == 2
