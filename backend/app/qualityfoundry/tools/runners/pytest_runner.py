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

            # 执行 pytest
            cwd = Path(working_dir) if working_dir else None

            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=request.timeout_s - 5,  # 留 5s 安全边界
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    return ctx.timeout(f"pytest timed out after {request.timeout_s}s")

            except FileNotFoundError:
                return ctx.failed("pytest not found. Please install pytest.")
            except Exception as e:
                return ctx.failed(f"Failed to execute pytest: {e}")

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode

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
