"""QualityFoundry - Sandbox Execution (L3 执行层隔离)

为工具执行提供进程级沙箱隔离能力。

Features:
- 硬超时（asyncio.wait_for）
- 路径白名单验证
- 环境变量清洗
- 资源监控（软限制）

Usage:
    config = SandboxConfig(timeout_s=60, allowed_paths=["tests/"])
    result = await run_in_sandbox(["python", "-m", "pytest"], config=config)
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SandboxConfig(BaseModel):
    """沙箱配置

    控制进程执行的安全边界。
    """

    timeout_s: int = Field(default=300, ge=1, description="硬超时（秒）")
    memory_limit_mb: int = Field(
        default=512, ge=64, description="内存软限制（MB），仅监控告警"
    )
    allowed_paths: list[str] = Field(
        default_factory=lambda: ["tests/", "test/", "artifacts/"],
        description="路径白名单（支持 glob）",
    )
    env_whitelist: list[str] = Field(
        default_factory=lambda: [
            # Core system (Unix/Mac)
            "PATH", "HOME", "USER", "SHELL", "TERM", "TMPDIR", "TMP", "TEMP",
            # Windows system (required for pytest/subprocess on Windows)
            "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "USERPROFILE",
            "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES",
            "PROGRAMFILES(X86)", "COMMONPROGRAMFILES", "SYSTEMDRIVE",
            # Python
            "PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "VIRTUAL_ENV",
            # Locale
            "LANG", "LC_*", "LANGUAGE",
            # CI/CD environments
            "CI", "GITHUB_*", "RUNNER_*", "ACTIONS_*",
            # Playwright / Browser
            "PLAYWRIGHT_*", "DISPLAY", "XDG_*", "DBUS_*",
            # QualityFoundry
            "QF_*",
        ],
        description="环境变量白名单（支持 glob）",
    )
    blocked_commands: list[str] = Field(
        default_factory=lambda: ["rm", "sudo", "chmod", "chown", "curl", "wget"],
        description="禁止的命令（首参数）",
    )


class SandboxResult(BaseModel):
    """沙箱执行结果"""

    exit_code: int = Field(description="进程退出码")
    stdout: str = Field(default="", description="标准输出")
    stderr: str = Field(default="", description="标准错误")
    elapsed_ms: int = Field(default=0, description="执行耗时（毫秒）")
    killed_by_timeout: bool = Field(default=False, description="是否因超时被杀死")
    resource_warning: str | None = Field(default=None, description="资源警告")
    sandbox_blocked: bool = Field(default=False, description="是否被沙箱阻止")
    block_reason: str | None = Field(default=None, description="阻止原因")


class SandboxViolationError(Exception):
    """沙箱违规错误"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Sandbox violation: {reason}")


def _match_glob_pattern(value: str, patterns: list[str]) -> bool:
    """检查值是否匹配任一 glob 模式"""
    for pattern in patterns:
        if fnmatch.fnmatch(value, pattern):
            return True
    return False


def _sanitize_env(whitelist: list[str]) -> dict[str, str]:
    """清洗环境变量，只保留白名单中的变量

    Args:
        whitelist: 环境变量白名单（支持 glob，如 "QF_*"）

    Returns:
        过滤后的环境变量字典
    """
    result: dict[str, str] = {}
    for key, value in os.environ.items():
        if _match_glob_pattern(key, whitelist):
            result[key] = value
    return result


def _validate_path(path: str | Path, allowed_paths: list[str]) -> bool:
    """验证路径是否在白名单中

    Args:
        path: 要验证的路径
        allowed_paths: 允许的路径前缀列表

    Returns:
        是否允许访问
    """
    path_str = str(path)

    # 禁止路径穿越
    if ".." in path_str:
        return False

    # 禁止绝对路径（除非在白名单中明确指定）
    if os.path.isabs(path_str):
        # 检查是否匹配白名单中的绝对路径模式
        for allowed in allowed_paths:
            if os.path.isabs(allowed) and path_str.startswith(allowed):
                return True
        return False

    # 检查相对路径前缀
    normalized = Path(path_str)
    parts = normalized.parts
    if not parts:
        return False

    # 跨平台兼容：使用 Path 来获取第一部分，不依赖特定分隔符
    first_part = parts[0].rstrip("/\\")
    for allowed in allowed_paths:
        # 使用 Path 来正确解析 allowed_paths（跨平台）
        allowed_norm = Path(allowed.rstrip("/\\"))
        allowed_first = allowed_norm.parts[0] if allowed_norm.parts else allowed.rstrip("/\\")
        if first_part == allowed_first:
            return True

    return False


def _validate_command(cmd: list[str], config: SandboxConfig) -> tuple[bool, str | None]:
    """验证命令是否允许执行

    Args:
        cmd: 命令参数列表
        config: 沙箱配置

    Returns:
        (is_allowed, block_reason)
    """
    if not cmd:
        return False, "Empty command"

    # 获取基础命令名（去掉路径）
    base_cmd = os.path.basename(cmd[0])

    # 检查禁止的命令
    if base_cmd in config.blocked_commands:
        return False, f"Command '{base_cmd}' is blocked by sandbox policy"

    # 检查危险模式
    cmd_str = " ".join(cmd)
    dangerous_patterns = [
        r"\brm\s+-rf\b",
        r"\bsudo\b",
        r"\bchmod\s+777\b",
        r"\b>\s*/dev/",
        r"\|\s*sh\b",
        r"\|\s*bash\b",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, cmd_str, re.IGNORECASE):
            return False, f"Dangerous command pattern detected: {pattern}"

    return True, None


async def run_in_sandbox(
    cmd: list[str],
    *,
    config: SandboxConfig | None = None,
    cwd: Path | str | None = None,
    input_data: bytes | None = None,
) -> SandboxResult:
    """在受限环境中执行命令

    Args:
        cmd: 命令参数列表
        config: 沙箱配置（默认使用 SandboxConfig()）
        cwd: 工作目录
        input_data: 传递给进程的标准输入

    Returns:
        SandboxResult: 执行结果

    Raises:
        SandboxViolationError: 如果命令违反沙箱策略
    """
    if config is None:
        config = SandboxConfig()

    import time

    start_time = time.monotonic()

    # 1. 验证命令
    allowed, block_reason = _validate_command(cmd, config)
    if not allowed:
        logger.warning(f"Sandbox blocked command: {cmd}, reason: {block_reason}")
        return SandboxResult(
            exit_code=-1,
            sandbox_blocked=True,
            block_reason=block_reason,
            stderr=block_reason or "Command blocked",
        )

    # 2. 验证工作目录
    if cwd is not None:
        if not _validate_path(cwd, config.allowed_paths):
            reason = f"Working directory '{cwd}' not in allowed paths"
            logger.warning(f"Sandbox blocked cwd: {reason}")
            return SandboxResult(
                exit_code=-1,
                sandbox_blocked=True,
                block_reason=reason,
                stderr=reason,
            )

    # 3. 清洗环境变量
    sanitized_env = _sanitize_env(config.env_whitelist)

    # 4. 执行命令
    logger.info(f"Sandbox executing: {' '.join(cmd[:5])}{'...' if len(cmd) > 5 else ''}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if input_data else None,
            cwd=cwd,
            env=sanitized_env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=input_data),
                timeout=config.timeout_s,
            )
            killed_by_timeout = False
        except asyncio.TimeoutError:
            logger.warning(f"Sandbox timeout after {config.timeout_s}s, killing process")
            process.kill()
            await process.wait()
            killed_by_timeout = True
            stdout_bytes = b""
            stderr_bytes = f"Process killed by sandbox timeout ({config.timeout_s}s)".encode()

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        # 5. 构建结果
        return SandboxResult(
            exit_code=process.returncode or -1 if killed_by_timeout else process.returncode or 0,
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            elapsed_ms=elapsed_ms,
            killed_by_timeout=killed_by_timeout,
        )

    except FileNotFoundError:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return SandboxResult(
            exit_code=-1,
            stderr=f"Command not found: {cmd[0]}",
            elapsed_ms=elapsed_ms,
        )
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.exception("Sandbox execution failed")
        return SandboxResult(
            exit_code=-1,
            stderr=str(e),
            elapsed_ms=elapsed_ms,
        )


def get_default_sandbox_config() -> SandboxConfig:
    """获取默认沙箱配置（用于没有 policy 时的回退）"""
    return SandboxConfig()
