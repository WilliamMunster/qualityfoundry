"""QualityFoundry - Container Sandbox Unit Tests

测试容器沙箱模块（不依赖真实 Docker，使用 mock）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qualityfoundry.execution.container_sandbox import (
    ContainerNotAvailableError,
    ContainerSandboxConfig,
    ContainerSandboxResult,
    _detect_container_runtime,
    _is_container_runtime_available,
    is_container_mode_available,
    run_in_container,
)


class TestContainerSandboxConfig:
    """ContainerSandboxConfig 单元测试"""

    def test_default_config(self):
        config = ContainerSandboxConfig()
        assert config.image == "python:3.11-slim"
        assert config.timeout_s == 300
        assert config.memory_mb == 512
        assert config.cpus == 1.0
        assert config.pids_limit == 100
        assert config.network_disabled is True
        assert config.readonly_workspace is True

    def test_custom_config(self):
        config = ContainerSandboxConfig(
            image="python:3.12",
            timeout_s=60,
            memory_mb=1024,
            cpus=2.0,
            network_disabled=False,
        )
        assert config.image == "python:3.12"
        assert config.timeout_s == 60
        assert config.memory_mb == 1024
        assert config.cpus == 2.0
        assert config.network_disabled is False


class TestContainerSandboxResult:
    """ContainerSandboxResult 单元测试"""

    def test_success_result(self):
        result = ContainerSandboxResult(
            exit_code=0,
            stdout="test passed",
            stderr="",
            elapsed_ms=1000,
            container_id="abc123",
            image_hash="sha256abc",
        )
        assert result.exit_code == 0
        assert result.mode == "container"
        assert result.killed_by_timeout is False

    def test_timeout_result(self):
        result = ContainerSandboxResult(
            exit_code=-1,
            killed_by_timeout=True,
            elapsed_ms=60000,
        )
        assert result.killed_by_timeout is True


class TestRuntimeDetection:
    """容器运行时检测测试"""

    @patch("shutil.which")
    def test_docker_available(self, mock_which):
        mock_which.side_effect = lambda x: "/usr/bin/docker" if x == "docker" else None
        runtime = _detect_container_runtime()
        assert runtime == "docker"

    @patch("shutil.which")
    def test_podman_fallback(self, mock_which):
        mock_which.side_effect = lambda x: "/usr/bin/podman" if x == "podman" else None
        runtime = _detect_container_runtime()
        assert runtime == "podman"

    @patch("shutil.which")
    def test_no_runtime(self, mock_which):
        mock_which.return_value = None
        runtime = _detect_container_runtime()
        assert runtime is None

    @patch("shutil.which")
    def test_is_container_runtime_available(self, mock_which):
        mock_which.return_value = "/usr/bin/docker"
        available, name = _is_container_runtime_available()
        assert available is True
        assert name == "docker"


class TestRunInContainer:
    """run_in_container 函数测试（使用 mock）"""

    @pytest.fixture
    def config(self):
        return ContainerSandboxConfig(timeout_s=60)

    @pytest.fixture
    def workspace(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        return ws

    @pytest.fixture
    def output(self, tmp_path):
        out = tmp_path / "output"
        out.mkdir()
        return out

    @pytest.mark.asyncio
    @patch("shutil.which")
    async def test_container_not_available_raises(self, mock_which, config, workspace, output):
        mock_which.return_value = None
        
        with pytest.raises(ContainerNotAvailableError) as exc_info:
            await run_in_container(
                ["python", "-m", "pytest"],
                config=config,
                workspace_path=workspace,
                output_path=output,
            )
        
        assert "docker/podman" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("qualityfoundry.execution.container_sandbox._get_image_hash")
    @patch("qualityfoundry.execution.container_sandbox._is_container_runtime_available")
    @patch("asyncio.create_subprocess_exec")
    async def test_successful_execution(
        self, mock_subprocess, mock_runtime, mock_hash, config, workspace, output
    ):
        # Setup mocks
        mock_runtime.return_value = (True, "docker")
        mock_hash.return_value = "abc123def456"
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"test passed", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        result = await run_in_container(
            ["python", "-m", "pytest"],
            config=config,
            workspace_path=workspace,
            output_path=output,
        )
        
        assert result.exit_code == 0
        assert result.mode == "container"
        assert "test passed" in result.stdout
        mock_subprocess.assert_called_once()
        
        # Verify docker command structure
        call_args = mock_subprocess.call_args[0]
        assert call_args[0] == "docker"
        assert "run" in call_args
        assert "--network=none" in call_args
        assert "--rm" in call_args

    @pytest.mark.asyncio
    @patch("qualityfoundry.execution.container_sandbox._get_image_hash")
    @patch("qualityfoundry.execution.container_sandbox._is_container_runtime_available")
    @patch("asyncio.create_subprocess_exec")
    async def test_timeout_kills_container(
        self, mock_subprocess, mock_runtime, mock_hash, workspace, output
    ):
        # Short timeout config
        config = ContainerSandboxConfig(timeout_s=1)
        mock_runtime.return_value = (True, "docker")
        mock_hash.return_value = "abc123"
        
        # Mock process that times out
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = asyncio.TimeoutError()
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process
        
        result = await run_in_container(
            ["python", "-m", "pytest"],
            config=config,
            workspace_path=workspace,
            output_path=output,
        )
        
        assert result.killed_by_timeout is True
        # Exit code may vary depending on mock setup, key is killed_by_timeout=True

    @pytest.mark.asyncio
    @patch("qualityfoundry.execution.container_sandbox._get_image_hash")
    @patch("qualityfoundry.execution.container_sandbox._is_container_runtime_available")
    @patch("asyncio.create_subprocess_exec")
    async def test_network_disabled_by_default(
        self, mock_subprocess, mock_runtime, mock_hash, config, workspace, output
    ):
        mock_runtime.return_value = (True, "docker")
        mock_hash.return_value = "abc123"
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        await run_in_container(
            ["python", "-c", "print('hello')"],
            config=config,
            workspace_path=workspace,
            output_path=output,
        )
        
        call_args = mock_subprocess.call_args[0]
        assert "--network=none" in call_args

    @pytest.mark.asyncio
    @patch("qualityfoundry.execution.container_sandbox._get_image_hash")
    @patch("qualityfoundry.execution.container_sandbox._is_container_runtime_available")
    @patch("asyncio.create_subprocess_exec")
    async def test_readonly_workspace_mount(
        self, mock_subprocess, mock_runtime, mock_hash, config, workspace, output
    ):
        mock_runtime.return_value = (True, "docker")
        mock_hash.return_value = "abc123"
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        await run_in_container(
            ["python", "-c", "print('hello')"],
            config=config,
            workspace_path=workspace,
            output_path=output,
        )
        
        call_args = mock_subprocess.call_args[0]
        # Find the workspace mount argument
        for i, arg in enumerate(call_args):
            if arg == "-v" and i + 1 < len(call_args):
                mount_arg = call_args[i + 1]
                if "/workspace" in mount_arg:
                    assert ":ro" in mount_arg
                    break

    @pytest.mark.asyncio
    @patch("qualityfoundry.execution.container_sandbox._get_image_hash")
    @patch("qualityfoundry.execution.container_sandbox._is_container_runtime_available")
    @patch("asyncio.create_subprocess_exec")
    async def test_resource_limits_in_command(
        self, mock_subprocess, mock_runtime, mock_hash, workspace, output
    ):
        config = ContainerSandboxConfig(
            memory_mb=1024,
            cpus=2.0,
            pids_limit=50,
        )
        mock_runtime.return_value = (True, "docker")
        mock_hash.return_value = "abc123"
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        await run_in_container(
            ["python", "-c", "print('hello')"],
            config=config,
            workspace_path=workspace,
            output_path=output,
        )
        
        call_args = mock_subprocess.call_args[0]
        assert "--memory=1024m" in call_args
        assert "--cpus=2.0" in call_args
        assert "--pids-limit=50" in call_args
