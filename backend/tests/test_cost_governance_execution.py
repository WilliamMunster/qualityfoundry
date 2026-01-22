"""Tests for Cost Governance - Execution Layer (Phase 5.1 PR-1)

验证 execute_with_governance 的核心行为：
- timeout_s 强制超时
- max_retries 重试机制
- metrics 正确记录 (attempts, retries_used, timed_out)
"""

import asyncio
from uuid import uuid4

import pytest

from qualityfoundry.tools.base import execute_with_governance
from qualityfoundry.tools.contracts import (
    ToolMetrics,
    ToolRequest,
    ToolResult,
    ToolStatus,
)


# --- Fake tools for testing ---


async def fake_success_tool(request: ToolRequest) -> ToolResult:
    """Always succeeds."""
    return ToolResult(
        status=ToolStatus.SUCCESS,
        stdout="success",
        metrics=ToolMetrics(),
    )


async def fake_fail_tool(request: ToolRequest) -> ToolResult:
    """Always fails."""
    return ToolResult(
        status=ToolStatus.FAILED,
        error_message="intentional failure",
        metrics=ToolMetrics(),
    )


async def fake_slow_tool(request: ToolRequest) -> ToolResult:
    """Sleeps longer than typical timeout."""
    await asyncio.sleep(10)  # 10 seconds
    return ToolResult(
        status=ToolStatus.SUCCESS,
        stdout="should not reach here",
        metrics=ToolMetrics(),
    )


class FailThenSucceedTool:
    """Fails N times, then succeeds."""

    def __init__(self, fail_count: int):
        self.fail_count = fail_count
        self.call_count = 0

    async def __call__(self, request: ToolRequest) -> ToolResult:
        self.call_count += 1
        if self.call_count <= self.fail_count:
            return ToolResult(
                status=ToolStatus.FAILED,
                error_message=f"failure {self.call_count}",
                metrics=ToolMetrics(),
            )
        return ToolResult(
            status=ToolStatus.SUCCESS,
            stdout=f"success after {self.call_count} attempts",
            metrics=ToolMetrics(),
        )


# --- Test Classes ---


class TestGovernanceTimeout:
    """超时强制测试"""

    @pytest.mark.asyncio
    async def test_timeout_triggers_on_slow_tool(self):
        """timeout_s=0.1 时慢工具必须触发超时"""
        request = ToolRequest(
            tool_name="slow_tool",
            run_id=uuid4(),
            args={},
            timeout_s=1,  # 1 second timeout, tool sleeps 10s
            max_retries=0,
        )

        result = await execute_with_governance(fake_slow_tool, request)

        assert result.status == ToolStatus.TIMEOUT
        assert result.metrics.timed_out is True
        assert result.metrics.attempts == 1
        assert result.metrics.retries_used == 0
        assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fast_tool_completes_within_timeout(self):
        """快速工具在超时前完成"""
        request = ToolRequest(
            tool_name="fast_tool",
            run_id=uuid4(),
            args={},
            timeout_s=10,
            max_retries=0,
        )

        result = await execute_with_governance(fake_success_tool, request)

        assert result.status == ToolStatus.SUCCESS
        assert result.metrics.timed_out is False
        assert result.metrics.attempts == 1


class TestGovernanceRetry:
    """重试机制测试"""

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        """成功时不应重试"""
        request = ToolRequest(
            tool_name="success_tool",
            run_id=uuid4(),
            args={},
            timeout_s=10,
            max_retries=3,
        )

        result = await execute_with_governance(fake_success_tool, request)

        assert result.status == ToolStatus.SUCCESS
        assert result.metrics.attempts == 1
        assert result.metrics.retries_used == 0

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """失败时应重试直到 max_retries"""
        request = ToolRequest(
            tool_name="fail_tool",
            run_id=uuid4(),
            args={},
            timeout_s=10,
            max_retries=3,
        )

        result = await execute_with_governance(fake_fail_tool, request)

        # 1 initial + 3 retries = 4 attempts
        assert result.status == ToolStatus.FAILED
        assert result.metrics.attempts == 4
        assert result.metrics.retries_used == 3

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """失败后重试成功"""
        tool = FailThenSucceedTool(fail_count=2)  # Fail twice, then succeed
        request = ToolRequest(
            tool_name="flaky_tool",
            run_id=uuid4(),
            args={},
            timeout_s=10,
            max_retries=3,
        )

        result = await execute_with_governance(tool, request)

        assert result.status == ToolStatus.SUCCESS
        assert result.metrics.attempts == 3  # 2 failures + 1 success
        assert result.metrics.retries_used == 2
        assert tool.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_when_max_retries_zero(self):
        """max_retries=0 时不重试"""
        request = ToolRequest(
            tool_name="fail_tool",
            run_id=uuid4(),
            args={},
            timeout_s=10,
            max_retries=0,
        )

        result = await execute_with_governance(fake_fail_tool, request)

        assert result.status == ToolStatus.FAILED
        assert result.metrics.attempts == 1
        assert result.metrics.retries_used == 0


class TestGovernanceMetrics:
    """治理指标测试"""

    @pytest.mark.asyncio
    async def test_metrics_fields_exist(self):
        """验证 metrics 包含所有治理字段"""
        request = ToolRequest(
            tool_name="success_tool",
            run_id=uuid4(),
            args={},
            timeout_s=10,
            max_retries=0,
        )

        result = await execute_with_governance(fake_success_tool, request)

        assert hasattr(result.metrics, "attempts")
        assert hasattr(result.metrics, "retries_used")
        assert hasattr(result.metrics, "timed_out")
        assert hasattr(result.metrics, "duration_ms")

    @pytest.mark.asyncio
    async def test_duration_ms_tracks_total_time(self):
        """duration_ms 应跟踪总执行时间"""
        request = ToolRequest(
            tool_name="success_tool",
            run_id=uuid4(),
            args={},
            timeout_s=10,
            max_retries=0,
        )

        result = await execute_with_governance(fake_success_tool, request)

        assert result.metrics.duration_ms >= 0


class TestGovernanceCombined:
    """组合场景测试"""

    @pytest.mark.asyncio
    async def test_timeout_with_retry(self):
        """超时后重试"""
        request = ToolRequest(
            tool_name="slow_tool",
            run_id=uuid4(),
            args={},
            timeout_s=1,  # 1 second timeout
            max_retries=2,
        )

        result = await execute_with_governance(fake_slow_tool, request)

        # Should timeout 3 times (1 initial + 2 retries)
        assert result.status == ToolStatus.TIMEOUT
        assert result.metrics.timed_out is True
        assert result.metrics.attempts == 3
        assert result.metrics.retries_used == 2
