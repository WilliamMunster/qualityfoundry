import pytest
from uuid import uuid4
from unittest.mock import MagicMock
from qualityfoundry.tools.contracts import ToolRequest, ToolStatus
from qualityfoundry.tools.runners.playwright_tool import run_playwright
from qualityfoundry.governance.policy_loader import PolicyConfig, SandboxPolicy, ArtifactLimits
from qualityfoundry.execution.container_sandbox import ContainerSandboxConfig, run_in_container

@pytest.mark.asyncio
async def test_playwright_container_gate_enforced(monkeypatch):
    """验证 Playwright 强制要求容器模式"""
    # 模拟非容器模式的 policy
    mock_policy = PolicyConfig(
        sandbox=SandboxPolicy(enabled=True, mode="subprocess")
    )
    import qualityfoundry.governance.policy_loader as pl
    monkeypatch.setattr(pl, "_cached_policy", mock_policy)
    
    request = ToolRequest(
        tool_name="run_playwright",
        run_id=uuid4(),
        args={"actions": []}
    )
    
    result = await run_playwright(request)
    
    assert result.status == ToolStatus.FAILED
    assert "Security Error" in result.error_message
    assert "container" in result.error_message

@pytest.mark.asyncio
async def test_playwright_gate_allows_container(monkeypatch):
    """验证 Playwright 允许容器模式（模拟执行失败以跳过真实浏览器启动）"""
    mock_policy = PolicyConfig(
        sandbox=SandboxPolicy(enabled=True, mode="container")
    )
    import qualityfoundry.governance.policy_loader as pl
    monkeypatch.setattr(pl, "_cached_policy", mock_policy)
    
    request = ToolRequest(
        tool_name="run_playwright",
        run_id=uuid4(),
        args={"actions": []}
    )
    
    # 我们只运行到进入 ctx 后的第一个 check (missing actions)
    result = await run_playwright(request)
    
    # 应该是 failed("No actions provided") 而不是 Security Error
    assert "No actions provided" in result.error_message

@pytest.mark.asyncio
async def test_artifact_count_limit(monkeypatch):
    """验证产物数量限制"""
    mock_policy = PolicyConfig(
        artifact_limits=ArtifactLimits(max_count=2)
    )
    import qualityfoundry.governance.policy_loader as pl
    monkeypatch.setattr(pl, "_cached_policy", mock_policy)
    
    from qualityfoundry.tools.base import ToolExecutionContext
    from qualityfoundry.tools.contracts import ArtifactRef, ArtifactType
    
    request = ToolRequest(tool_name="test_tool", run_id=uuid4())
    async with ToolExecutionContext(
        request, 
        max_artifact_count=2
    ) as ctx:
        # 添加 3 个产物
        ctx.add_artifact(ArtifactRef(type=ArtifactType.LOG, path="1.log", size=10))
        ctx.add_artifact(ArtifactRef(type=ArtifactType.LOG, path="2.log", size=10))
        ctx.add_artifact(ArtifactRef(type=ArtifactType.LOG, path="3.log", size=10))
        
        assert len(ctx._artifacts) == 2

@pytest.mark.asyncio
async def test_artifact_size_limit(monkeypatch):
    """验证单个产物大小限制"""
    # 限制 1MB
    request = ToolRequest(tool_name="test_tool", run_id=uuid4())
    from qualityfoundry.tools.base import ToolExecutionContext
    from qualityfoundry.tools.contracts import ArtifactRef, ArtifactType

    async with ToolExecutionContext(
        request, 
        max_artifact_size_mb=1
    ) as ctx:
        # 添加一个 2MB 的产物
        large_ref = ArtifactRef(type=ArtifactType.OTHER, path="large.bin", size=2 * 1024 * 1024)
        ctx.add_artifact(large_ref)
        
        assert len(ctx._artifacts) == 0
        
        # 添加一个 0.5MB 的产物
        small_ref = ArtifactRef(type=ArtifactType.OTHER, path="small.bin", size=512 * 1024)
        ctx.add_artifact(small_ref)
        
        assert len(ctx._artifacts) == 1

@pytest.mark.asyncio
async def test_container_sandbox_network_policy(monkeypatch):
    """验证容器网络策略正确映射到 Docker 命令参数"""
    from pathlib import Path
    import asyncio
    
    # 模拟容器运行时可用
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/docker" if x == "docker" else None)
    
    # 模拟 subprocess 执行，用于捕获命令
    mock_proc = MagicMock()
    mock_proc.communicate = asyncio.iscoroutinefunction(lambda: None) # Make it awaitable
    async def mock_communicate():
        return b"stdout", b"stderr"
    mock_proc.communicate = mock_communicate
    mock_proc.returncode = 0
    
    captured_cmds = []
    async def mock_create_subprocess_exec(*args, **kwargs):
        captured_cmds.append(list(args))
        return mock_proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create_subprocess_exec)
    
    # 路径准备
    workspace = Path("/tmp/ws")
    output = Path("/tmp/out")
    
    # 1. 测试 deny 模式
    config_deny = ContainerSandboxConfig(network_policy="deny")
    await run_in_container(["ls"], config=config_deny, workspace_path=workspace, output_path=output)
    assert "--network=none" in captured_cmds[-1]
    
    # 2. 测试 all 模式
    config_all = ContainerSandboxConfig(network_policy="all")
    await run_in_container(["ls"], config=config_all, workspace_path=workspace, output_path=output)
    # 不应该包含 --network=none
    assert "--network=none" not in captured_cmds[-1]
    
    # 3. 测试 allowlist 模式 (未实现回退到 deny)
    config_allow = ContainerSandboxConfig(network_policy="allowlist", network_allowlist=[])
    await run_in_container(["ls"], config=config_allow, workspace_path=workspace, output_path=output)
    assert "--network=none" in captured_cmds[-1]
