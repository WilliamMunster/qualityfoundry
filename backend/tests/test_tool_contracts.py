"""Tests for Tool Contracts (PR-1)

验证统一 Tool Schema 的正确性。
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolMetrics,
    ToolRequest,
    ToolResult,
    ToolStatus,
)


class TestArtifactRef:
    """ArtifactRef 测试"""

    def test_basic_creation(self):
        """基本创建"""
        ref = ArtifactRef(
            type=ArtifactType.SCREENSHOT,
            path="/tmp/screenshot.png",
            mime="image/png",
            size=1024,
        )
        assert ref.type == ArtifactType.SCREENSHOT
        assert ref.path == "/tmp/screenshot.png"
        assert ref.mime == "image/png"
        assert ref.size == 1024
        assert ref.sha256 is None

    def test_from_file(self):
        """从文件创建"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake png content")
            f.flush()
            path = Path(f.name)

        ref = ArtifactRef.from_file(path, ArtifactType.SCREENSHOT)
        assert ref.type == ArtifactType.SCREENSHOT
        assert ref.mime == "image/png"
        assert ref.size > 0

        # 清理
        path.unlink()

    def test_from_file_with_hash(self):
        """从文件创建并计算 hash"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            f.flush()
            path = Path(f.name)

        ref = ArtifactRef.from_file(path, ArtifactType.LOG, compute_hash=True)
        assert ref.sha256 is not None
        assert len(ref.sha256) == 64  # SHA256 hex length

        path.unlink()

    def test_from_nonexistent_file(self):
        """不存在的文件"""
        ref = ArtifactRef.from_file("/nonexistent/file.png", ArtifactType.SCREENSHOT)
        assert ref.path == "/nonexistent/file.png"
        assert ref.size == 0


class TestToolRequest:
    """ToolRequest 测试"""

    def test_basic_creation(self):
        """基本创建"""
        run_id = uuid4()
        req = ToolRequest(
            tool_name="run_pytest",
            run_id=run_id,
            args={"test_path": "tests/"},
        )
        assert req.tool_name == "run_pytest"
        assert req.run_id == run_id
        assert req.args == {"test_path": "tests/"}
        assert req.timeout_s == 120  # 默认值
        assert req.dry_run is False

    def test_with_custom_timeout(self):
        """自定义超时"""
        req = ToolRequest(
            tool_name="run_playwright",
            run_id=uuid4(),
            timeout_s=300,
        )
        assert req.timeout_s == 300

    def test_timeout_validation(self):
        """超时验证"""
        with pytest.raises(ValueError):
            ToolRequest(
                tool_name="test",
                run_id=uuid4(),
                timeout_s=0,  # 必须 >= 1
            )

        with pytest.raises(ValueError):
            ToolRequest(
                tool_name="test",
                run_id=uuid4(),
                timeout_s=4000,  # 必须 <= 3600
            )


class TestToolResult:
    """ToolResult 测试"""

    def test_success_factory(self):
        """成功工厂方法"""
        result = ToolResult.success(stdout="test passed")
        assert result.status == ToolStatus.SUCCESS
        assert result.ok is True
        assert result.stdout == "test passed"
        assert result.error_message is None

    def test_failed_factory(self):
        """失败工厂方法"""
        result = ToolResult.failed(
            error_message="Test failed",
            stderr="AssertionError",
        )
        assert result.status == ToolStatus.FAILED
        assert result.ok is False
        assert result.error_message == "Test failed"
        assert result.stderr == "AssertionError"

    def test_timeout_factory(self):
        """超时工厂方法"""
        result = ToolResult.timeout()
        assert result.status == ToolStatus.TIMEOUT
        assert result.ok is False
        assert "timed out" in result.error_message.lower()

    def test_with_artifacts(self):
        """带 artifacts"""
        artifacts = [
            ArtifactRef(type=ArtifactType.SCREENSHOT, path="/tmp/shot.png"),
            ArtifactRef(type=ArtifactType.JUNIT_XML, path="/tmp/junit.xml"),
        ]
        result = ToolResult.success(artifacts=artifacts)
        assert len(result.artifacts) == 2
        assert result.artifacts[0].type == ArtifactType.SCREENSHOT

    def test_with_metrics(self):
        """带 metrics"""
        metrics = ToolMetrics(
            duration_ms=5000,
            steps_total=10,
            steps_passed=8,
            steps_failed=2,
        )
        result = ToolResult.success(metrics=metrics)
        assert result.metrics.duration_ms == 5000
        assert result.metrics.steps_passed == 8
        assert result.duration_ms == 5000  # property

    def test_datetime_serialization(self):
        """时间序列化"""
        now = datetime.now(timezone.utc)
        result = ToolResult.success(started_at=now, ended_at=now)

        # 序列化
        data = result.model_dump(mode="json")
        assert data["started_at"].endswith("Z")
        assert data["ended_at"].endswith("Z")

    def test_to_json_log(self):
        """转换为 JSON 日志"""
        metrics = ToolMetrics(duration_ms=1234)
        result = ToolResult.success(metrics=metrics)

        log = result.to_json_log()
        assert log["status"] == "success"
        assert log["ok"] is True
        assert log["duration_ms"] == 1234
        assert log["artifacts_count"] == 0
        assert log["error"] is None


class TestToolMetrics:
    """ToolMetrics 测试"""

    def test_defaults(self):
        """默认值"""
        metrics = ToolMetrics()
        assert metrics.duration_ms == 0
        assert metrics.exit_code is None
        assert metrics.steps_total == 0
        assert metrics.retries == 0

    def test_extra_fields(self):
        """额外字段（ConfigDict extra='allow'）"""
        metrics = ToolMetrics(
            duration_ms=1000,
            custom_field="custom_value",
        )
        assert metrics.duration_ms == 1000
        assert metrics.custom_field == "custom_value"
