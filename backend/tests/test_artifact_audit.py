import pytest
from qualityfoundry.database.run_event_models import RunEvent  # noqa: F401 - 强制注册
from uuid import uuid4
from unittest.mock import MagicMock, patch
from qualityfoundry.tools.runners.pytest_runner import _collect_artifacts
from qualityfoundry.tools.runners.playwright_tool import run_playwright
from qualityfoundry.tools.contracts import ArtifactRef, ArtifactType, ToolRequest
from qualityfoundry.services.audit_service import write_artifact_collected_event

def test_write_artifact_collected_event_structure():
    """验证通用审计函数的 Payload 结构与脱敏策略。"""
    db = MagicMock()
    run_id = uuid4()
    artifacts = [
        ArtifactRef(type=ArtifactType.SCREENSHOT, path="/abs/path/to/shot1.png", size=100, metadata={"rel_path": "ui/shot1.png"}),
        ArtifactRef(type=ArtifactType.LOG, path="/abs/path/to/app.log", size=200),  # 无 rel_path，应降级为文件名
    ]
    
    with patch("qualityfoundry.services.audit_service.write_audit_event") as mock_write:
        write_artifact_collected_event(
            db,
            run_id=run_id,
            tool_name="test_tool",
            artifacts=artifacts,
            scope=["test_scope"],
            extensions=[".png", ".log"]
        )
        
        mock_write.assert_called_once()
        _, kwargs = mock_write.call_args
        details = kwargs["details"]
        
        # 结构验证
        assert details["total_count"] == 2
        assert details["stats_by_type"]["screenshot"] == 1
        assert details["stats_by_type"]["log"] == 1
        
        # 脱敏验证
        samples = details["samples"]
        assert samples[0]["rel_path"] == "ui/shot1.png"
        assert samples[1]["rel_path"] == "app.log"  # 降级脱敏
        assert "/abs/path" not in str(samples)

def test_pytest_runner_triggers_generalized_audit(tmp_path):
    """验证 pytest_runner 是否调用了通用的审计服务。"""
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "test.log").write_text("log")
    
    ctx = MagicMock()
    ctx.artifact_dir = artifact_dir
    ctx.request = ToolRequest(tool_name="run_pytest", run_id=uuid4(), args={"test_path": "tests/"})
    ctx._artifacts = []
    def add_artifact(art): ctx._artifacts.append(art)
    ctx.add_artifact = add_artifact
    
    with patch("qualityfoundry.database.config.SessionLocal"), \
         patch("qualityfoundry.services.audit_service.write_artifact_collected_event") as mock_gen_audit:
        
        _collect_artifacts(ctx, 0)
        mock_gen_audit.assert_called_once()
        _, kwargs = mock_gen_audit.call_args
        assert kwargs["tool_name"] == "run_pytest"
        assert "repro" in kwargs["scope"]

@pytest.mark.asyncio
async def test_run_playwright_triggers_audit(tmp_path):
    """验证 run_playwright 是否成功接入了产物审计。"""
    # 准备物理文件以通过 ArtifactRef.from_file 的 stat 检查
    artifact_dir = tmp_path / "artifacts"
    ui_dir = artifact_dir / "ui"
    ui_dir.mkdir(parents=True)
    screenshot_file = ui_dir / "s1.png"
    screenshot_file.write_text("fake image content")
    
    trace_file = artifact_dir / "trace.zip"
    trace_file.write_text("fake trace content")

    request = ToolRequest(
        tool_name="run_playwright",
        run_id=uuid4(),
        args={"actions": [{"type": "goto", "url": "http://test"}]}
    )
    
    # 模拟 run_actions 返回证据 (必须是已存在的物理路径)
    evidence = [MagicMock(screenshot=str(screenshot_file), ok=True, index=0)]
    
    with patch("qualityfoundry.tools.runners.playwright_tool.get_policy") as mock_policy_getter, \
         patch("qualityfoundry.tools.runners.playwright_tool.run_actions", return_value=(True, evidence, str(trace_file))), \
         patch("qualityfoundry.database.config.SessionLocal"), \
         patch("qualityfoundry.services.audit_service.write_artifact_collected_event") as mock_gen_audit:
        
        # 确保 policy 满足 Playwright 运行门禁 (container mode)
        mock_policy = MagicMock()
        mock_policy.sandbox.enabled = True
        mock_policy.sandbox.mode = "container"
        mock_policy.artifact_limits.max_count = 50
        mock_policy.artifact_limits.max_size_mb = 10
        mock_policy_getter.return_value = mock_policy

        # 注入 mock artifact_dir
        with patch("qualityfoundry.tools.base.get_artifact_dir", return_value=artifact_dir):
            await run_playwright(request)
        
        # 验证审计被触发
        mock_gen_audit.assert_called_once()
        _, kwargs = mock_gen_audit.call_args
        assert kwargs["tool_name"] == "run_playwright"
        # 验证包含了截图和 trace
        assert any("s1.png" in str(a.path) for a in kwargs["artifacts"])
        assert any("trace.zip" in str(a.path) for a in kwargs["artifacts"])
