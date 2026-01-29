"""QualityFoundry - Container Sandbox (L3 强隔离层)

为 run_pytest 提供容器级隔离能力（Docker/Podman）。

Features:
- 禁网 (--network none)
- 只读挂载 workspace
- 可写输出目录 (artifacts)
- 资源硬限制 (memory, cpus, pids)
- 超时硬 kill (docker kill)

fallback: 若 docker 不可用，返回明确错误，不降级执行。

Usage:
    config = ContainerSandboxConfig(image="python:3.11-slim", timeout_s=60)
    result = await run_in_container(cmd, config, workspace_path, output_path)
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContainerSandboxConfig(BaseModel):
    """容器沙箱配置

    扩展自 policy.sandbox，增加容器特有字段。
    """

    image: str = Field(
        default="python:3.11-slim",
        description="Docker 镜像名称"
    )
    timeout_s: int = Field(default=300, ge=1, description="硬超时（秒）")
    memory_mb: int = Field(default=512, ge=64, description="内存限制（MB）")
    cpus: float = Field(default=1.0, ge=0.1, description="CPU 核数限制")
    pids_limit: int = Field(default=100, ge=10, description="进程数限制")
    network_policy: str = Field(
        default="deny",
        pattern="^(deny|allowlist|all)$",
        description="网络策略: deny (禁用), allowlist (允许白名单), all (完全开放)"
    )
    network_allowlist: list[str] = Field(default_factory=list, description="域名/IP 白名单")
    readonly_workspace: bool = Field(default=True, description="workspace 只读挂载")


class ContainerSandboxResult(BaseModel):
    """容器沙箱执行结果"""

    exit_code: int = Field(description="容器退出码")
    stdout: str = Field(default="", description="标准输出")
    stderr: str = Field(default="", description="标准错误")
    elapsed_ms: int = Field(default=0, description="执行耗时（毫秒）")
    killed_by_timeout: bool = Field(default=False, description="是否因超时被杀死")
    container_id: Optional[str] = Field(default=None, description="容器 ID (短)")
    image_hash: Optional[str] = Field(default=None, description="镜像 SHA256 (短)")
    mode: str = Field(default="container", description="执行模式标识")


class ContainerNotAvailableError(Exception):
    """容器运行时不可用"""
    pass


def _detect_container_runtime() -> Optional[str]:
    """检测可用的容器运行时
    
    Returns:
        "docker" | "podman" | None
    """
    for runtime in ["docker", "podman"]:
        if shutil.which(runtime):
            return runtime
    return None


def _is_container_runtime_available() -> tuple[bool, Optional[str]]:
    """检查容器运行时是否可用
    
    Returns:
        (is_available, runtime_name)
    """
    runtime = _detect_container_runtime()
    return (runtime is not None, runtime)


async def _get_image_hash(runtime: str, image: str) -> Optional[str]:
    """获取镜像 SHA256 (前16位) 用于审计"""
    try:
        proc = await asyncio.create_subprocess_exec(
            runtime, "inspect", "--format", "{{.Id}}", image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode == 0:
            full_hash = stdout.decode().strip()
            # 格式: sha256:abc123... -> 取前16位
            if ":" in full_hash:
                return full_hash.split(":")[1][:16]
            return full_hash[:16]
    except Exception:
        pass
    return None


async def run_in_container(
    cmd: list[str],
    *,
    config: ContainerSandboxConfig,
    workspace_path: Path,
    output_path: Path,
    env_vars: Optional[dict[str, str]] = None,
) -> ContainerSandboxResult:
    """在容器中执行命令

    Args:
        cmd: 命令参数列表（在容器内执行）
        config: 容器沙箱配置
        workspace_path: 工作目录（只读挂载到 /workspace）
        output_path: 输出目录（可写挂载到 /output）
        env_vars: 传递给容器的环境变量

    Returns:
        ContainerSandboxResult

    Raises:
        ContainerNotAvailableError: 如果 docker/podman 不可用
    """
    start_time = time.monotonic()

    # 1. 检查容器运行时
    available, runtime = _is_container_runtime_available()
    if not available:
        raise ContainerNotAvailableError(
            "Container runtime (docker/podman) not found. "
            "Install Docker or set sandbox.mode=subprocess in policy."
        )

    # 确保 runtime 是 str（类型收窄）
    assert runtime is not None

    # 2. 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)

    # 3. 获取镜像 hash（用于审计）
    image_hash = await _get_image_hash(runtime, config.image)

    # 4. 构建 docker run 命令
    container_name = f"qf-sandbox-{int(time.time())}-{os.getpid()}"
    
    docker_cmd = [
        runtime, "run",
        "--name", container_name,
        "--rm",  # 自动清理
        # 资源限制
        f"--memory={config.memory_mb}m",
        f"--cpus={config.cpus}",
        f"--pids-limit={config.pids_limit}",
        # 安全
        "--security-opt", "no-new-privileges",
        "--cap-drop=ALL",
    ]

    # 5. 网络策略
    if config.network_policy == "deny":
        docker_cmd.append("--network=none")
    elif config.network_policy == "allowlist":
        # 简单实现：由于 Docker 原生不支持按域名过滤，这里仅作标识
        # 实际生产环境通常配合 iptables 或 sidecar 开启
        # 此处展示逻辑骨架：如果限制白名单但未实现，则回退到 deny 保证安全
        if not config.network_allowlist:
            docker_cmd.append("--network=none")
        else:
            # MVP 阶段：白名单模式若无专用 sidecar 则暂视为 all 但记录警告
            logger.warning("Container network allowlist requested but not implemented for runtime. Using default network.")
            pass 
    else:
        # "all" 模式，不添加限制
        pass

    # 挂载
    workspace_mount = f"{workspace_path.absolute()}:/workspace"
    if config.readonly_workspace:
        workspace_mount += ":ro"
    docker_cmd.extend(["-v", workspace_mount])
    docker_cmd.extend(["-v", f"{output_path.absolute()}:/output:rw"])

    # 工作目录
    docker_cmd.extend(["-w", "/workspace"])

    # 环境变量
    if env_vars:
        for k, v in env_vars.items():
            docker_cmd.extend(["-e", f"{k}={v}"])
    # 传递 CI 标识
    if os.environ.get("CI"):
        docker_cmd.extend(["-e", "CI=true"])

    # 镜像和命令
    docker_cmd.append(config.image)
    docker_cmd.extend(cmd)

    logger.info(f"Container sandbox: {runtime} run {config.image} (network={config.network_policy})")

    # 5. 执行
    killed_by_timeout = False

    try:
        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=config.timeout_s,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Container timeout after {config.timeout_s}s, killing...")
            killed_by_timeout = True
            # 强制杀死容器
            try:
                kill_proc = await asyncio.create_subprocess_exec(
                    runtime, "kill", container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(kill_proc.wait(), timeout=5)
            except Exception:
                pass
            # 等待原进程结束
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except Exception:
                process.kill()
            stdout_bytes = b""
            stderr_bytes = f"Container killed by timeout ({config.timeout_s}s)".encode()

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return ContainerSandboxResult(
            exit_code=process.returncode if process.returncode is not None else -1,
            stdout=stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else "",
            stderr=stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else "",
            elapsed_ms=elapsed_ms,
            killed_by_timeout=killed_by_timeout,
            container_id=container_name[:12],
            image_hash=image_hash,
            mode="container",
        )

    except FileNotFoundError:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        raise ContainerNotAvailableError(f"Container runtime '{runtime}' not found in PATH")
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.exception("Container sandbox execution failed")
        return ContainerSandboxResult(
            exit_code=-1,
            stderr=str(e),
            elapsed_ms=elapsed_ms,
            mode="container",
        )


def is_container_mode_available() -> bool:
    """检查容器模式是否可用（供 policy 逻辑检测）
    
    目前强隔离容器模式仅在 Linux 下支持。
    """
    import sys
    if sys.platform != "linux":
        return False
    available, _ = _is_container_runtime_available()
    return available
