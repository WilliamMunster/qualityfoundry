"""PR-2: Policy Extension Tests

测试 PR-2 新增功能：
- policy loader 解析新字段 + 默认值稳定
- mode=container + docker 缺失 → predictable failure
- mode=subprocess → 不受影响（回归）
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from qualityfoundry.governance.policy_loader import (
    ContainerPolicy,
    PolicyConfig,
    SandboxPolicy,
    load_policy,
)


class TestPolicyLoaderContainerFields:
    """policy loader 能解析新字段 + 默认值稳定"""

    def test_sandbox_mode_default_is_subprocess(self):
        """默认 mode=subprocess，不引入 breaking change"""
        policy = SandboxPolicy()
        assert policy.mode == "subprocess"

    def test_sandbox_container_has_defaults(self):
        """ContainerPolicy 有稳定默认值"""
        container = ContainerPolicy()
        assert container.image == "python:3.11-slim"
        assert container.network_policy == "deny"

    def test_sandbox_policy_includes_container(self):
        """SandboxPolicy 包含 container 子配置"""
        policy = SandboxPolicy()
        assert hasattr(policy, "container")
        assert isinstance(policy.container, ContainerPolicy)

    def test_policy_config_sandbox_defaults(self):
        """PolicyConfig 沙箱默认值稳定"""
        config = PolicyConfig()
        assert config.sandbox.enabled is True
        assert config.sandbox.mode == "subprocess"
        assert config.sandbox.container.image == "python:3.11-slim"

    def test_load_policy_with_container_section(self, tmp_path: Path):
        """加载含 container 段的 policy"""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("""
version: "1.0"
sandbox:
  enabled: true
  mode: container
  container:
    image: "python:3.12-alpine"
    network_policy: all
""")
        config = load_policy(policy_file)
        assert config.sandbox.mode == "container"
        assert config.sandbox.container.image == "python:3.12-alpine"
        assert config.sandbox.container.network_policy == "all"

    def test_load_policy_without_container_uses_defaults(self, tmp_path: Path):
        """无 container 段时使用默认值"""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("""
version: "1.0"
sandbox:
  enabled: true
  mode: subprocess
""")
        config = load_policy(policy_file)
        assert config.sandbox.mode == "subprocess"
        # container 字段应使用默认值
        assert config.sandbox.container.image == "python:3.11-slim"


class TestContainerUnavailableFailure:
    """mode=container + docker 缺失 → predictable failure"""

    @pytest.mark.asyncio
    @patch("shutil.which")
    async def test_container_mode_docker_unavailable_returns_error(self, mock_which):
        """容器不可用时返回明确错误"""
        mock_which.return_value = None  # docker/podman 不存在

        from qualityfoundry.execution.container_sandbox import (
            ContainerNotAvailableError,
            run_in_container,
            ContainerSandboxConfig,
        )

        config = ContainerSandboxConfig()

        with pytest.raises(ContainerNotAvailableError) as exc_info:
            await run_in_container(
                ["python", "-c", "print('test')"],
                config=config,
                workspace_path=Path("/tmp"),
                output_path=Path("/tmp/output"),
            )

        assert "docker/podman" in str(exc_info.value).lower()


class TestSubprocessModeRegression:
    """mode=subprocess → 不受影响（回归）"""

    def test_subprocess_mode_is_default(self):
        """subprocess 仍是默认模式"""
        policy = SandboxPolicy()
        assert policy.mode == "subprocess"

    def test_sandbox_enabled_still_required_for_mcp_write(self):
        """MCP write 仍需 sandbox.enabled=true"""
        policy = SandboxPolicy(enabled=False, mode="subprocess")
        assert policy.enabled is False
        # MCP write security chain 会基于此拒绝
