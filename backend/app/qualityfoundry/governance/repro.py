"""QualityFoundry - Reproducibility Metadata

提供可复现性元数据收集，用于 evidence.json 的 repro 区块。

功能：
- Git 信息（SHA, branch, dirty status）
- Python 运行时信息
- 依赖指纹（pyproject.toml / requirements.txt 的 SHA256）
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ReproMeta(BaseModel):
    """可复现性元数据"""
    
    git_sha: Optional[str] = Field(default=None, description="Git commit SHA")
    git_branch: Optional[str] = Field(default=None, description="Git branch name")
    git_dirty: Optional[bool] = Field(default=None, description="Working tree has uncommitted changes")
    python_version: str = Field(..., description="Python version (e.g., '3.14.2')")
    platform_info: str = Field(..., description="Platform info (e.g., 'darwin-arm64')")
    deps_fingerprint: Optional[str] = Field(default=None, description="Hash of deps file (e.g., 'sha256:abc123')")
    deps_fingerprint_algo: str = Field(default="sha256", description="Hash algorithm used for deps fingerprint")
    deps_source: Optional[str] = Field(default=None, description="Source file for deps (e.g., 'pyproject.toml')")



def _run_git_command(args: list[str], cwd: Path | None = None) -> str | None:
    """安全执行 git 命令，失败时返回 None"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def get_git_sha(cwd: Path | None = None) -> str | None:
    """获取当前 Git commit SHA
    
    优先级：
    1. GITHUB_SHA 环境变量（CI 环境）
    2. git rev-parse HEAD 命令
    """
    # 优先使用 CI 环境变量
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha
    
    # Fallback 到 git 命令
    return _run_git_command(["rev-parse", "HEAD"], cwd)


def get_git_branch(cwd: Path | None = None) -> str | None:
    """获取当前 Git 分支名
    
    优先级：
    1. GITHUB_REF_NAME 环境变量（CI 环境）
    2. git branch --show-current 命令
    """
    # 优先使用 CI 环境变量
    branch = os.environ.get("GITHUB_REF_NAME")
    if branch:
        return branch
    
    # Fallback 到 git 命令
    return _run_git_command(["branch", "--show-current"], cwd)


def get_git_dirty(cwd: Path | None = None) -> bool | None:
    """检查工作区是否有未提交的更改"""
    status = _run_git_command(["status", "--porcelain"], cwd)
    if status is None:
        return None
    return len(status) > 0


def get_deps_fingerprint(project_root: Path | None = None) -> tuple[str | None, str | None]:
    """计算依赖文件的 SHA256 指纹
    
    优先级：
    1. pyproject.toml
    2. requirements.txt
    
    Returns:
        (fingerprint, source_file) 或 (None, None)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # 优先查找 pyproject.toml
    candidates = [
        ("pyproject.toml", project_root / "pyproject.toml"),
        ("requirements.txt", project_root / "requirements.txt"),
    ]
    
    for name, path in candidates:
        if path.exists() and path.is_file():
            try:
                content = path.read_bytes()
                fingerprint = hashlib.sha256(content).hexdigest()
                return f"sha256:{fingerprint}", name
            except (OSError, IOError):
                continue
    
    return None, None


def get_platform_info() -> str:
    """获取平台信息（OS-架构）"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    return f"{system}-{machine}"


def get_python_version() -> str:
    """获取 Python 版本"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_repro_meta(project_root: Path | None = None) -> ReproMeta:
    """收集完整的可复现性元数据
    
    Args:
        project_root: 项目根目录（用于查找 deps 文件和执行 git 命令）
        
    Returns:
        ReproMeta 实例
    """
    deps_fingerprint, deps_source = get_deps_fingerprint(project_root)
    
    return ReproMeta(
        git_sha=get_git_sha(project_root),
        git_branch=get_git_branch(project_root),
        git_dirty=get_git_dirty(project_root),
        python_version=get_python_version(),
        platform_info=get_platform_info(),
        deps_fingerprint=deps_fingerprint,
        deps_source=deps_source,
    )
