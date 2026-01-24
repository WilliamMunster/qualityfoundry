"""QualityFoundry - Sandbox 单元测试

测试沙箱执行的核心功能：
- 正常命令执行
- 超时处理
- 路径白名单
- 命令阻止
- 环境变量清洗
"""

import os
import pytest

from qualityfoundry.execution.sandbox import (
    SandboxConfig,
    run_in_sandbox,
    _validate_path,
    _validate_command,
    _sanitize_env,
    _match_glob_pattern,
)


class TestSandboxConfig:
    """SandboxConfig 模型测试"""

    def test_default_values(self):
        """默认值应符合预期"""
        config = SandboxConfig()
        assert config.timeout_s == 300
        assert config.memory_limit_mb == 512
        assert "tests/" in config.allowed_paths
        assert "PATH" in config.env_whitelist

    def test_custom_values(self):
        """自定义值应正确设置"""
        config = SandboxConfig(
            timeout_s=60,
            memory_limit_mb=256,
            allowed_paths=["custom/"],
        )
        assert config.timeout_s == 60
        assert config.memory_limit_mb == 256
        assert config.allowed_paths == ["custom/"]


class TestPathValidation:
    """路径白名单验证测试"""

    def test_allowed_tests_path(self):
        """tests/ 目录应被允许"""
        assert _validate_path("tests/unit/test_foo.py", ["tests/"]) is True

    def test_allowed_test_path(self):
        """test/ 目录应被允许"""
        assert _validate_path("test/integration", ["test/"]) is True

    def test_blocked_parent_traversal(self):
        """路径穿越应被阻止"""
        assert _validate_path("../etc/passwd", ["tests/"]) is False
        assert _validate_path("tests/../../../etc", ["tests/"]) is False

    def test_blocked_absolute_path(self):
        """绝对路径应被阻止（除非在白名单中）"""
        assert _validate_path("/etc/passwd", ["tests/"]) is False
        assert _validate_path("/home/user/tests", ["tests/"]) is False

    def test_allowed_absolute_in_whitelist(self):
        """白名单中的绝对路径应被允许"""
        assert _validate_path("/tmp/sandbox", ["/tmp/"]) is True

    def test_blocked_unrecognized_path(self):
        """未识别的路径应被阻止"""
        assert _validate_path("src/main.py", ["tests/"]) is False
        assert _validate_path("node_modules/", ["tests/"]) is False


class TestCommandValidation:
    """命令验证测试"""

    def test_allowed_python(self):
        """python 命令应被允许"""
        config = SandboxConfig()
        allowed, reason = _validate_command(["python", "-m", "pytest"], config)
        assert allowed is True
        assert reason is None

    def test_blocked_rm(self):
        """rm 命令应被阻止"""
        config = SandboxConfig()
        allowed, reason = _validate_command(["rm", "-rf", "/"], config)
        assert allowed is False
        assert "rm" in reason

    def test_blocked_sudo(self):
        """sudo 命令应被阻止"""
        config = SandboxConfig()
        allowed, reason = _validate_command(["sudo", "apt", "install"], config)
        assert allowed is False
        assert "sudo" in reason

    def test_blocked_dangerous_pattern(self):
        """危险模式应被阻止"""
        config = SandboxConfig(blocked_commands=[])  # 移除命令阻止，测试模式检测
        allowed, reason = _validate_command(["echo", "foo", "|", "sh"], config)
        assert allowed is False
        assert "pattern" in reason.lower()

    def test_empty_command(self):
        """空命令应被阻止"""
        config = SandboxConfig()
        allowed, reason = _validate_command([], config)
        assert allowed is False


class TestEnvSanitization:
    """环境变量清洗测试"""

    def test_path_preserved(self):
        """PATH 应被保留"""
        env = _sanitize_env(["PATH"])
        assert "PATH" in env

    def test_unknown_removed(self):
        """未知变量应被移除"""
        os.environ["SANDBOX_TEST_SECRET"] = "secret"
        try:
            env = _sanitize_env(["PATH"])
            assert "SANDBOX_TEST_SECRET" not in env
        finally:
            del os.environ["SANDBOX_TEST_SECRET"]

    def test_glob_pattern(self):
        """glob 模式应生效"""
        os.environ["QF_TEST_VAR"] = "value"
        try:
            env = _sanitize_env(["QF_*"])
            assert "QF_TEST_VAR" in env
        finally:
            del os.environ["QF_TEST_VAR"]


class TestGlobMatching:
    """Glob 模式匹配测试"""

    def test_exact_match(self):
        """精确匹配"""
        assert _match_glob_pattern("PATH", ["PATH"]) is True

    def test_wildcard_suffix(self):
        """通配符后缀"""
        assert _match_glob_pattern("QF_DEBUG", ["QF_*"]) is True
        assert _match_glob_pattern("QF_", ["QF_*"]) is True

    def test_no_match(self):
        """不匹配"""
        assert _match_glob_pattern("SECRET", ["PATH", "HOME"]) is False


class TestRunInSandbox:
    """run_in_sandbox 集成测试"""

    @pytest.mark.asyncio
    async def test_simple_echo(self):
        """简单 echo 命令"""
        result = await run_in_sandbox(["echo", "hello"])
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.sandbox_blocked is False

    @pytest.mark.asyncio
    async def test_python_version(self):
        """Python 版本命令"""
        result = await run_in_sandbox(["python", "--version"])
        assert result.exit_code == 0
        assert "Python" in result.stdout or "Python" in result.stderr

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self):
        """超时应杀死进程"""
        config = SandboxConfig(timeout_s=1)
        result = await run_in_sandbox(["sleep", "10"], config=config)
        assert result.killed_by_timeout is True
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_blocked_command(self):
        """阻止的命令应返回错误"""
        result = await run_in_sandbox(["sudo", "ls"])
        assert result.sandbox_blocked is True
        assert result.block_reason is not None
        assert "sudo" in result.block_reason

    @pytest.mark.asyncio
    async def test_blocked_cwd(self):
        """非法工作目录应被阻止"""
        config = SandboxConfig(allowed_paths=["tests/"])
        result = await run_in_sandbox(["ls"], config=config, cwd="/etc")
        assert result.sandbox_blocked is True
        assert "not in allowed paths" in result.block_reason

    @pytest.mark.asyncio
    async def test_command_not_found(self):
        """不存在的命令"""
        result = await run_in_sandbox(["nonexistent_command_xyz"])
        assert result.exit_code == -1
        assert "not found" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_elapsed_time_recorded(self):
        """执行耗时应被记录"""
        result = await run_in_sandbox(["sleep", "0.1"])
        assert result.elapsed_ms >= 50  # 至少 50ms
