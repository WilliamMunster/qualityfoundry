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

import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from qualityfoundry.tools.base import ToolExecutionContext, log_tool_result
from qualityfoundry.tools.config import truncate_output
from qualityfoundry.tools.contracts import (
    ArtifactRef,
    ArtifactType,
    ToolRequest,
    ToolResult,
)

if TYPE_CHECKING:
    from qualityfoundry.execution.sandbox import SandboxConfig, SandboxResult
    from qualityfoundry.execution.container_sandbox import (
        ContainerSandboxConfig,
        ContainerSandboxResult,
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


async def _log_sandbox_audit(
    run_id,
    tool_name: str,
    config: "SandboxConfig",
    result: "SandboxResult",
) -> None:
    """记录沙箱执行审计事件

    只记录 hash/摘要，不记录敏感路径明文，遵循最小信息暴露原则。

    Args:
        run_id: 运行 ID
        tool_name: 工具名称
        config: 沙箱配置
        result: 沙箱执行结果
    """
    import hashlib

    try:
        from qualityfoundry.database.config import SessionLocal
        from qualityfoundry.database.audit_log_models import AuditEventType
        from qualityfoundry.services.audit_service import write_audit_event

        # 计算配置摘要（hash），不暴露明文路径
        allowed_paths_hash = hashlib.sha256(
            ",".join(sorted(config.allowed_paths)).encode()
        ).hexdigest()[:16]
        env_whitelist_hash = hashlib.sha256(
            ",".join(sorted(config.env_whitelist)).encode()
        ).hexdigest()[:16]

        # 审计记录只包含安全的元数据
        details = {
            "enabled": True,
            "timeout_s": config.timeout_s,
            "memory_limit_mb": config.memory_limit_mb,
            "allowed_paths_hash": allowed_paths_hash,
            "env_whitelist_hash": env_whitelist_hash,
            "killed_by_timeout": result.killed_by_timeout,
            "resource_warning_present": result.resource_warning is not None,
            "elapsed_ms": result.elapsed_ms,
            "sandbox_blocked": result.sandbox_blocked,
        }

        # 使用 SessionLocal 直接创建会话（不依赖 FastAPI 依赖注入）
        with SessionLocal() as db:
            write_audit_event(
                db,
                run_id=run_id,
                event_type=AuditEventType.SANDBOX_EXEC,
                tool_name=tool_name,
                status="blocked" if result.sandbox_blocked else (
                    "timeout" if result.killed_by_timeout else "completed"
                ),
                duration_ms=result.elapsed_ms,
                details=details,
            )

    except Exception:
        # 审计失败不应阻止工具执行
        logger.warning("Failed to log sandbox audit event", exc_info=True)


async def _log_container_sandbox_audit(
    run_id,
    tool_name: str,
    config: "ContainerSandboxConfig",
    result: "ContainerSandboxResult",
) -> None:
    """记录容器沙箱执行审计事件

    Args:
        run_id: 运行 ID
        tool_name: 工具名称
        config: 容器沙箱配置
        result: 容器沙箱执行结果
    """
    try:
        from qualityfoundry.database.config import SessionLocal
        from qualityfoundry.database.audit_log_models import AuditEventType
        from qualityfoundry.services.audit_service import write_audit_event

        details = {
            "mode": "container",
            "image": config.image,
            "image_hash": result.image_hash,
            "container_id": result.container_id,
            "timeout_s": config.timeout_s,
            "memory_mb": config.memory_mb,
            "cpus": config.cpus,
            "network_disabled": config.network_disabled,
            "readonly_workspace": config.readonly_workspace,
            "killed_by_timeout": result.killed_by_timeout,
            "elapsed_ms": result.elapsed_ms,
        }

        with SessionLocal() as db:
            write_audit_event(
                db,
                run_id=run_id,
                event_type=AuditEventType.SANDBOX_EXEC,
                tool_name=tool_name,
                status="timeout" if result.killed_by_timeout else "completed",
                duration_ms=result.elapsed_ms,
                details=details,
            )

    except Exception:
        logger.warning("Failed to log container sandbox audit event", exc_info=True)


async def _log_container_unavailable_audit(
    run_id,
    tool_name: str,
    error_message: str,
) -> None:
    """记录容器不可用审计事件 (等价于 SANDBOX_VIOLATION)

    Args:
        run_id: 运行 ID
        tool_name: 工具名称
        error_message: 错误信息
    """
    try:
        from qualityfoundry.database.config import SessionLocal
        from qualityfoundry.database.audit_log_models import AuditEventType
        from qualityfoundry.services.audit_service import write_audit_event

        details = {
            "mode": "container",
            "violation_type": "container_unavailable",
            "error": error_message,
        }

        with SessionLocal() as db:
            write_audit_event(
                db,
                run_id=run_id,
                event_type=AuditEventType.SANDBOX_EXEC,
                tool_name=tool_name,
                status="blocked",
                duration_ms=0,
                details=details,
            )

    except Exception:
        logger.warning("Failed to log container unavailable audit event", exc_info=True)


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



async def run_pytest(
    request: ToolRequest,
    *,
    sandbox_config: "SandboxConfig | None" = None,
    sandbox_mode: str = "subprocess",
    container_config: "ContainerSandboxConfig | None" = None,
) -> ToolResult:
    """Pytest 工具：执行测试并生成 JUnit XML

    Args:
        request: ToolRequest，args 包含：
            - test_path: str - 测试文件或目录路径（必填）
            - markers: str (可选) - pytest markers，如 "not slow"
            - extra_args: list[str] (可选) - 额外的 pytest 参数
            - working_dir: str (可选) - 工作目录
        sandbox_config: 沙箱配置（由 ToolRegistry 基于 policy 注入）
        sandbox_mode: 沙箱模式 - "subprocess" 或 "container"
        container_config: 容器配置（当 sandbox_mode=container 时由 registry 注入）

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
            # 使用 sys.executable 确保使用当前运行环境的 Python
            import sys
            cmd = [
                sys.executable, "-m", "pytest",
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
            
            # 设置产物目录环境变量，供测试脚本（如 Playwright）使用
            env = os.environ.copy()
            env["QUALITYFOUNDRY_ARTIFACT_DIR"] = str(ctx.artifact_dir)

            # 执行 pytest
            cwd = Path(working_dir) if working_dir else None

            # 容器模式优先
            if sandbox_mode == "container" and container_config is not None:
                from qualityfoundry.execution.container_sandbox import (
                    run_in_container,
                    ContainerNotAvailableError,
                )

                logger.info(f"Container sandbox: image={container_config.image}")
                
                # 容器模式需要确定 workspace 和 output 路径
                workspace_path = Path(working_dir) if working_dir else Path.cwd()
                output_path = ctx.artifact_dir
                
                # 容器内命令：路径重映射到 /workspace, /output
                container_cmd = [
                    "python", "-m", "pytest",
                    "-q",
                    "--junitxml=/output/junit.xml",
                    test_path,
                ]
                if markers:
                    container_cmd.extend(["-m", markers])
                if extra_args:
                    container_cmd.extend(extra_args)

                try:
                    container_result = await run_in_container(
                        container_cmd,
                        config=container_config,
                        workspace_path=workspace_path,
                        output_path=output_path,
                    )
                except ContainerNotAvailableError as e:
                    # 审计容器不可用事件 (等价于 SANDBOX_VIOLATION)
                    await _log_container_unavailable_audit(
                        run_id=request.run_id,
                        tool_name="run_pytest",
                        error_message=str(e),
                    )
                    return ctx.failed(
                        f"Container sandbox unavailable: {e}. "
                        "Set sandbox.mode=subprocess in policy to use fallback."
                    )

                # 容器审计
                await _log_container_sandbox_audit(
                    run_id=request.run_id,
                    tool_name="run_pytest",
                    config=container_config,
                    result=container_result,
                )

                if container_result.killed_by_timeout:
                    return ctx.timeout(f"pytest timed out after {container_config.timeout_s}s (container)")

                stdout = container_result.stdout
                stderr = container_result.stderr
                exit_code = container_result.exit_code

            # subprocess 沙箱模式
            elif sandbox_config is not None:
                # Sandbox 路径：policy 启用沙箱
                from qualityfoundry.execution.sandbox import run_in_sandbox

                logger.info(f"Subprocess sandbox: timeout={sandbox_config.timeout_s}s")
                sandbox_result = await run_in_sandbox(cmd, config=sandbox_config, cwd=cwd, env=env)

                # B3: 审计沙箱执行（只记录 hash/摘要，不记录敏感路径明文）
                await _log_sandbox_audit(
                    run_id=request.run_id,
                    tool_name="run_pytest",
                    config=sandbox_config,
                    result=sandbox_result,
                )

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
                
            else:
                # Legacy 路径：policy 禁用沙箱或直接调用（不经过 registry）
                import asyncio

                logger.info("Sandbox disabled by policy, using legacy subprocess")
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=env,
                    )
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=request.timeout_s,
                    )
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    exit_code = process.returncode or 0
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    return ctx.timeout(f"pytest timed out after {request.timeout_s}s")

            # 收集 artifacts (JUnit XML & 业务产物)
            _collect_artifacts(ctx, exit_code)

            # P1: 额外记录 UI/Playwright 跳过原因 (如果存在)
            if "ui" in test_path or "playwright" in test_path:
                ui_dir = ctx.artifact_dir / "ui"
                ui_dir.mkdir(parents=True, exist_ok=True)
                status_file = ui_dir / "playwright_status.json"
                
                # 情况 A：JUnit XML 显示有跳过
                if junit_path.exists():
                    stats = _parse_junit_stats(junit_path)
                    if stats.get("skipped", 0) > 0:
                        import json
                        with open(status_file, "w") as f:
                            json.dump({
                                "status": "skipped",
                                "reason": f"Pytest reported {stats['skipped']} skipped tests in UI suite. Likely due to environment mismatch or missing browser.",
                                "ts": str(ctx.request.run_id) # Using run_id as a dummy TS anchor
                            }, f)
                
                # 情况 B：执行异常且没有生成 junit.xml (可能是环境崩溃)
                elif exit_code != 0:
                    import json
                    with open(status_file, "w") as f:
                        json.dump({
                            "status": "error",
                            "reason": f"Execution failed with code {exit_code} before JUnit report generation. Check logs for environment errors.",
                            "ts": str(ctx.request.run_id)
                        }, f)

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


def _collect_artifacts(ctx: ToolExecutionContext, exit_code: int) -> None:
    """收集测试产物，包括 JUnit XML 和指定的业务产物 (ui/, http/, repro/)。"""
    artifact_dir = ctx.artifact_dir
    junit_path = artifact_dir / "junit.xml"

    # 1. 扫描特定目录和后缀 (有边界的收集)
    # 目录: ui/, http/, repro/
    # 后缀: .json, .xml, .png, .jpg, .webp, .txt, .log
    allowed_dirs = ["ui", "http", "repro"]
    allowed_exts = [".json", ".xml", ".png", ".jpg", ".webp", ".txt", ".log"]
    
    # 递归扫描 artifact_dir
    for root, dirs, files in os.walk(artifact_dir):
        rel_root = Path(root).relative_to(artifact_dir)
        
        # 只处理根目录或允许的子目录
        if rel_root != Path(".") and rel_root.parts[0] not in allowed_dirs:
            continue
            
        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            
            if ext in allowed_exts:
                # 确定 ArtifactType
                if ext in {".png", ".jpg", ".jpeg", ".webp"}:
                    atype = ArtifactType.SCREENSHOT
                elif file == "junit.xml":
                    atype = ArtifactType.JUNIT_XML
                elif ext == ".json":
                    atype = ArtifactType.OTHER
                else:
                    atype = ArtifactType.LOG
                
                artifact = ArtifactRef.from_file(file_path, atype)
                # 显式保存相对路径和预览标识，用于前端展示和证据预览
                rel_path = file_path.relative_to(artifact_dir)
                artifact.metadata["rel_path"] = str(rel_path.as_posix())
                
                # 如果是图像，确保标记为 IMAGE 以便前端直接启用预览
                if atype == ArtifactType.SCREENSHOT:
                    artifact.metadata["is_image"] = True
                    # 提示：实际预览 URL 由后端统一在 API 层拼装，此处打标即可
                
                ctx.add_artifact(artifact)
    
    # 3. 记录产物审计日志
    if ctx._artifacts:
        try:
            from qualityfoundry.database.config import SessionLocal
            from qualityfoundry.services.audit_service import write_artifact_collected_event

            with SessionLocal() as db:
                write_artifact_collected_event(
                    db,
                    run_id=ctx.request.run_id,
                    tool_name=ctx.request.tool_name,
                    artifacts=ctx._artifacts,
                    scope=allowed_dirs,
                    extensions=allowed_exts,
                )
        except Exception:
            logger.warning("Failed to log artifact audit event", exc_info=True)

    # 4. 解析 JUnit XML 获取统计
    if junit_path.exists():
        stats = _parse_junit_stats(junit_path)
        ctx.update_metrics(
            exit_code=exit_code,
            steps_total=stats.get("tests", 0),
            steps_passed=stats.get("tests", 0) - stats.get("failures", 0) - stats.get("errors", 0),
            steps_failed=stats.get("failures", 0) + stats.get("errors", 0),
        )
    else:
        ctx.update_metrics(exit_code=exit_code)


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
