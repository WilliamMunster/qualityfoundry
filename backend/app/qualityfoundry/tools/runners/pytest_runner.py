"""QualityFoundry - Pytest Runner Tool

执行 pytest 测试并收集 JUnit XML 报告。

使用方式：
    request = ToolRequest(
        tool_name="run_pytest",
        run_id=uuid4(),
        args={
            "test_path": "tests/",           # 必填
            "markers": "not slow",           # 可选: pytest markers
            "extra_args": ["-v", "--tb=short"],  # 可选: 额外参数
        }
    )
    result = await run_pytest(request)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import sys
from pathlib import Path

from qualityfoundry.tools.base import ToolExecutionContext, log_tool_result
from qualityfoundry.tools.config import truncate_output
from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolRequest,
    ToolResult,
)

logger = logging.getLogger(__name__)

# 允许的测试路径前缀（安全白名单）
ALLOWED_TEST_PATHS = frozenset({
    "tests",
    "test",
    "tests/",
    "test/",
})

# 项目根目录（用于路径验证）
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def _collect_environment_diagnostics() -> dict[str, str | None]:
    """Collect environment diagnostics for troubleshooting tool failures.

    Returns:
        Dict with diagnostic info: python_path, python_version, pytest_available,
        venv_active, path_summary
    """
    diag: dict[str, str | None] = {}

    # Python info
    diag["python_executable"] = sys.executable
    diag["python_version"] = sys.version.split()[0]

    # Check pytest availability
    pytest_path = shutil.which("pytest")
    diag["pytest_in_path"] = pytest_path if pytest_path else "NOT FOUND"

    # Check python -m pytest availability
    python_m_pytest = shutil.which("python")
    diag["python_in_path"] = python_m_pytest if python_m_pytest else "NOT FOUND"

    # Virtual environment detection
    venv = os.environ.get("VIRTUAL_ENV")
    diag["virtual_env"] = venv if venv else "NOT SET"

    # PATH summary (first 3 entries for brevity)
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    diag["path_first_3"] = os.pathsep.join(path_entries[:3]) if path_entries else "EMPTY"

    # Current working directory
    diag["cwd"] = os.getcwd()

    return diag


def _format_diagnostics(diag: dict[str, str | None]) -> str:
    """Format diagnostics dict as readable string for error messages."""
    lines = ["Environment diagnostics:"]
    for key, value in diag.items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def _is_safe_test_path(test_path: str) -> bool:
    """验证测试路径是否安全（防止路径穿越）

    Rules:
    - 不允许 ..
    - 必须以 tests/ 或 test/ 开头，或者是具体的 test_*.py 文件
    - 不允许绝对路径
    """
    # 禁止路径穿越
    if ".." in test_path:
        return False

    # 禁止绝对路径
    if os.path.isabs(test_path):
        return False

    # 规范化路径
    normalized = Path(test_path)
    parts = normalized.parts

    if not parts:
        return False

    # 允许 tests/ 或 test/ 目录
    first_part = parts[0].rstrip("/")
    if first_part in ("tests", "test"):
        return True

    # 允许直接指定 test_*.py 文件（但必须在当前目录或 tests/ 下）
    if len(parts) == 1 and parts[0].startswith("test_") and parts[0].endswith(".py"):
        return True

    return False


async def run_pytest(request: ToolRequest) -> ToolResult:
    """Pytest 工具：执行测试并生成 JUnit XML

    Args:
        request: ToolRequest，args 包含：
            - test_path: str - 测试文件或目录路径（必填）
            - markers: str (可选) - pytest markers，如 "not slow"
            - extra_args: list[str] (可选) - 额外的 pytest 参数
            - working_dir: str (可选) - 工作目录

    Returns:
        ToolResult: 统一的执行结果，artifacts 包含 junit.xml
    """
    async with ToolExecutionContext(request) as ctx:
        try:
            args = request.args

            # 验证必填参数
            test_path = args.get("test_path")
            if not test_path:
                return ctx.failed("Missing required argument: test_path")

            # 安全验证
            if not _is_safe_test_path(test_path):
                return ctx.failed(
                    f"Invalid test_path: {test_path}. "
                    "Path must start with 'tests/' or 'test/' and cannot contain '..'"
                )

            # 解析可选参数
            markers = args.get("markers")
            extra_args = args.get("extra_args", [])
            working_dir = args.get("working_dir")

            # JUnit XML 输出路径 (使用正斜杠以确保跨平台兼容性，pytest 会处理)
            junit_path = ctx.artifact_dir / "junit.xml"
            junit_path_str = str(junit_path).replace("\\", "/")
            
            # 构建 pytest 命令
            cmd = [
                "python", "-m", "pytest",
                "-q",
                f"--junitxml={junit_path_str}",
                test_path,
            ]

            # 添加 markers
            if markers:
                cmd.extend(["-m", markers])

            # 添加额外参数
            if extra_args:
                cmd.extend(extra_args)

            logger.info(f"Running pytest: {' '.join(cmd)}")

            # 执行 pytest (通过沙箱)
            cwd = Path(working_dir) if working_dir else None

            # 使用沙箱执行
            from qualityfoundry.execution.sandbox import run_in_sandbox, SandboxConfig

            # 从 request 获取沙箱配置，如果没有则使用默认值
            sandbox_config = getattr(request, "sandbox_config", None) or SandboxConfig(
                timeout_s=request.timeout_s - 5,  # 留 5s 安全边界
                allowed_paths=["tests/", "test/", "artifacts/"],
            )

            sandbox_result = await run_in_sandbox(cmd, config=sandbox_config, cwd=cwd)

            # 检查沙箱是否阻止了命令
            if sandbox_result.sandbox_blocked:
                return ctx.failed(
                    f"Sandbox blocked: {sandbox_result.block_reason}"
                )

            # 检查超时
            if sandbox_result.killed_by_timeout:
                return ctx.timeout(f"pytest timed out after {sandbox_config.timeout_s}s")

            stdout = sandbox_result.stdout
            stderr = sandbox_result.stderr
            exit_code = sandbox_result.exit_code

            # 收集 JUnit XML artifact
            if junit_path.exists():
                artifact = ArtifactRef.from_file(junit_path, ArtifactType.JUNIT_XML)
                ctx.add_artifact(artifact)

                # 解析 JUnit XML 获取统计
                stats = _parse_junit_stats(junit_path)
                ctx.update_metrics(
                    exit_code=exit_code,
                    steps_total=stats.get("tests", 0),
                    steps_passed=stats.get("tests", 0) - stats.get("failures", 0) - stats.get("errors", 0),
                    steps_failed=stats.get("failures", 0) + stats.get("errors", 0),
                )

            else:
                ctx.update_metrics(exit_code=exit_code)

            # 判断结果
            if exit_code == 0:
                result = ctx.success(
                    stdout=truncate_output(stdout),
                    raw_output={
                        "exit_code": exit_code,
                        "junit_path": str(junit_path) if junit_path.exists() else None,
                    },
                )
            else:
                result = ctx.failed(
                    error_message=f"pytest exited with code {exit_code}",
                    stderr=truncate_output(stderr),
                )
                result.stdout = truncate_output(stdout)
                result.raw_output = {
                    "exit_code": exit_code,
                    "junit_path": str(junit_path) if junit_path.exists() else None,
                }

            log_tool_result(result, "run_pytest")
            return result

        except Exception as e:
            logger.exception("run_pytest failed")
            return ctx.failed(error_message=str(e))


def _parse_junit_stats(junit_path: Path) -> dict:
    """解析 JUnit XML 获取测试统计

    Returns:
        dict with keys: tests, failures, errors, skipped, time
    """
    try:
        content = junit_path.read_text()
        stats = {}

        # 简单正则解析 testsuite 属性
        # <testsuite ... tests="4" errors="0" failures="1" skipped="0" time="0.123">
        patterns = [
            (r'tests="(\d+)"', "tests"),
            (r'failures="(\d+)"', "failures"),
            (r'errors="(\d+)"', "errors"),
            (r'skipped="(\d+)"', "skipped"),
            (r'time="([\d.]+)"', "time"),
        ]

        for pattern, key in patterns:
            match = re.search(pattern, content)
            if match:
                value = match.group(1)
                stats[key] = float(value) if key == "time" else int(value)

        return stats
    except Exception as e:
        logger.warning(f"Failed to parse JUnit XML: {e}")
        return {}


# 工具元数据（用于注册）
TOOL_METADATA = {
    "name": "run_pytest",
    "description": "Execute pytest tests and generate JUnit XML report",
    "version": "1.0.0",
    "tags": ["testing", "pytest", "junit"],
}
