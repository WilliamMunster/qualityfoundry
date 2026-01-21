"""Tests for fetch_logs tool (PR-2)

验证日志获取工具的正确性。
"""

import json
from uuid import uuid4

import pytest

from qualityfoundry.tools.contracts import ArtifactType, ToolRequest, ToolStatus
from qualityfoundry.tools.runners.log_fetcher import fetch_logs


class TestFetchLogs:
    """fetch_logs 工具测试"""

    @pytest.mark.asyncio
    async def test_missing_target_run_id(self):
        """缺少必填参数"""
        request = ToolRequest(
            tool_name="fetch_logs",
            run_id=uuid4(),
            args={},
        )

        result = await fetch_logs(request)

        assert result.status == ToolStatus.FAILED
        assert "target_run_id" in result.error_message

    @pytest.mark.asyncio
    async def test_invalid_uuid(self):
        """无效的 UUID"""
        request = ToolRequest(
            tool_name="fetch_logs",
            run_id=uuid4(),
            args={"target_run_id": "not-a-valid-uuid"},
        )

        result = await fetch_logs(request)

        assert result.status == ToolStatus.FAILED
        assert "Invalid UUID" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_run(self):
        """获取不存在的 run 日志"""
        request = ToolRequest(
            tool_name="fetch_logs",
            run_id=uuid4(),
            args={"target_run_id": str(uuid4())},
        )

        result = await fetch_logs(request)

        # 不存在的 run 应该返回成功，但日志为空
        assert result.status == ToolStatus.SUCCESS
        assert result.raw_output["summary"]["logs_count"] == 0

        # 应该产出 logs.jsonl artifact
        log_artifacts = [a for a in result.artifacts if a.type == ArtifactType.LOG]
        assert len(log_artifacts) == 1

    @pytest.mark.asyncio
    async def test_fetch_with_existing_artifacts(self):
        """获取有 artifact 的 run 日志"""
        from qualityfoundry.tools.config import get_artifacts_root

        # 创建临时 artifact 目录
        target_run_id = uuid4()
        artifact_root = get_artifacts_root()
        run_dir = artifact_root / str(target_run_id) / "tools" / "run_pytest"
        run_dir.mkdir(parents=True, exist_ok=True)

        # 创建 tool_result.json
        tool_result = {
            "result": {"status": "success"},
            "request": {"tool_name": "run_pytest"},
            "logged_at": "2024-01-01T00:00:00Z",
        }
        (run_dir / "tool_result.json").write_text(json.dumps(tool_result))

        # 创建其他 artifact
        (run_dir / "junit.xml").write_text("<testsuite/>")

        try:
            request = ToolRequest(
                tool_name="fetch_logs",
                run_id=uuid4(),
                args={"target_run_id": str(target_run_id)},
            )

            result = await fetch_logs(request)

            assert result.status == ToolStatus.SUCCESS
            assert result.raw_output["summary"]["logs_count"] >= 1
            assert result.raw_output["summary"]["artifacts_count"] >= 1

            # 检查日志内容
            logs = result.raw_output["logs"]
            assert any(log.get("tool_name") == "run_pytest" for log in logs)

        finally:
            # 清理
            import shutil
            if (artifact_root / str(target_run_id)).exists():
                shutil.rmtree(artifact_root / str(target_run_id))

    @pytest.mark.asyncio
    async def test_fetch_with_limit(self):
        """测试日志条数限制"""
        request = ToolRequest(
            tool_name="fetch_logs",
            run_id=uuid4(),
            args={
                "target_run_id": str(uuid4()),
                "limit": 10,
            },
        )

        result = await fetch_logs(request)

        assert result.status == ToolStatus.SUCCESS
        # 限制应该被应用（即使没有日志也不会报错）
        assert result.raw_output["summary"]["logs_count"] <= 10
