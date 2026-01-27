"""QualityFoundry - Container Sandbox 单元测试

测试容器沙箱的核心功能。
需在 Docker/Podman 可用的环境下运行。
"""

import pytest
from qualityfoundry.execution.container_sandbox import (
    ContainerSandboxConfig,
    run_in_container,
    is_container_mode_available,
)

# 检查容器运行时是否可用
CONTAINER_READY = is_container_mode_available()

@pytest.mark.skipif(not CONTAINER_READY, reason="需要 Docker 或 Podman 环境")
class TestContainerSandbox:
    """Container Sandbox 集成测试"""

    @pytest.mark.asyncio
    async def test_simple_echo(self, tmp_path):
        """测试基础 echo 命令"""
        config = ContainerSandboxConfig(image="python:3.11-slim", timeout_s=30)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        output = tmp_path / "output"
        output.mkdir()

        result = await run_in_container(
            ["echo", "hello-container"],
            config=config,
            workspace_path=workspace,
            output_path=output
        )

        assert result.exit_code == 0
        assert "hello-container" in result.stdout
        assert result.mode == "container"
    
    @pytest.mark.asyncio
    async def test_network_isolation(self, tmp_path):
        """测试禁网 (--network none)"""
        config = ContainerSandboxConfig(image="python:3.11-slim", timeout_s=30, network_disabled=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        output = tmp_path / "output"
        output.mkdir()

        # 尝试 ping (在禁网容器中应失败)
        # 注意：slim 镜像可能没有 ping，使用 python 尝试 socket 连接
        cmd = ["python", "-c", "import socket; socket.create_connection(('google.com', 80), timeout=1)"]
        
        result = await run_in_container(
            cmd,
            config=config,
            workspace_path=workspace,
            output_path=output
        )

        assert result.exit_code != 0
        assert "Temporary failure in name resolution" in result.stderr or "Network is unreachable" in result.stderr

    @pytest.mark.asyncio
    async def test_timeout_handling(self, tmp_path):
        """测试容器超时处理"""
        config = ContainerSandboxConfig(image="python:3.11-slim", timeout_s=2)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        output = tmp_path / "output"
        output.mkdir()

        result = await run_in_container(
            ["sleep", "10"],
            config=config,
            workspace_path=workspace,
            output_path=output
        )

        assert result.killed_by_timeout is True
        assert "killed by timeout" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_readonly_workspace(self, tmp_path):
        """测试工作目录只读挂载"""
        config = ContainerSandboxConfig(image="python:3.11-slim", timeout_s=30, readonly_workspace=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "test.txt").write_text("content")
        
        output = tmp_path / "output"
        output.mkdir()

        # 尝试写入只读目录应失败
        result = await run_in_container(
            ["touch", "/workspace/new-file.txt"],
            config=config,
            workspace_path=workspace,
            output_path=output
        )

        assert result.exit_code != 0
        assert "Read-only file system" in result.stderr
