"""
Reproducibility Metadata Tests

测试可复现性元数据收集功能
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

from qualityfoundry.governance.repro import (

    ReproMeta,
    get_repro_meta,
    get_git_sha,
    get_git_branch,
    get_git_dirty,
    get_deps_fingerprint,
    get_python_version,
    get_platform_info,
)


class TestReproMeta:
    """ReproMeta 模型测试"""

    def test_basic_fields(self):
        """测试基本字段"""
        meta = ReproMeta(
            git_sha="abc123",
            git_branch="main",
            git_dirty=False,
            python_version="3.14.2",
            platform_info="darwin-arm64",
            deps_fingerprint="sha256:xyz789",
            deps_source="pyproject.toml",
        )
        
        assert meta.git_sha == "abc123"
        assert meta.git_branch == "main"
        assert meta.git_dirty is False
        assert meta.python_version == "3.14.2"
        assert meta.platform_info == "darwin-arm64"
        assert meta.deps_fingerprint == "sha256:xyz789"
        assert meta.deps_source == "pyproject.toml"

    def test_optional_fields_default_to_none(self):
        """测试可选字段默认为 None"""
        meta = ReproMeta(
            python_version="3.14.2",
            platform_info="linux-x86_64",
        )
        
        assert meta.git_sha is None
        assert meta.git_branch is None
        assert meta.git_dirty is None
        assert meta.deps_fingerprint is None
        assert meta.deps_source is None


class TestGitSha:
    """git_sha 获取测试"""

    def test_from_github_sha_env(self):
        """测试从 GITHUB_SHA 环境变量获取"""
        with patch.dict(os.environ, {"GITHUB_SHA": "ci-commit-sha-123"}):
            sha = get_git_sha()
            assert sha == "ci-commit-sha-123"

    def test_fallback_to_git_command(self, tmp_path):
        """测试 fallback 到 git 命令"""
        with patch.dict(os.environ, {}, clear=True):
            # 清除 GITHUB_SHA
            os.environ.pop("GITHUB_SHA", None)
            # 在真实仓库中应该能获取到 SHA
            sha = get_git_sha(Path.cwd())
            # 可能有值也可能没有（取决于是否在 git 仓库中）
            assert sha is None or len(sha) == 40

    def test_graceful_failure(self):
        """测试 git 命令失败时的优雅降级"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_SHA", None)
            # 使用一个不存在的目录
            sha = get_git_sha(Path("/nonexistent/path"))
            assert sha is None


class TestGitBranch:
    """git_branch 获取测试"""

    def test_from_github_ref_name_env(self):
        """测试从 GITHUB_REF_NAME 环境变量获取"""
        with patch.dict(os.environ, {"GITHUB_REF_NAME": "feature/test-branch"}):
            branch = get_git_branch()
            assert branch == "feature/test-branch"

    def test_graceful_failure(self):
        """测试 git 命令失败时的优雅降级"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_REF_NAME", None)
            branch = get_git_branch(Path("/nonexistent/path"))
            assert branch is None


class TestGitDirty:
    """git_dirty 检测测试"""

    def test_graceful_failure(self):
        """测试 git 命令失败时返回 None"""
        dirty = get_git_dirty(Path("/nonexistent/path"))
        assert dirty is None


class TestDepsFingerprint:
    """依赖指纹测试"""

    def test_fingerprint_pyproject(self, tmp_path):
        """测试 pyproject.toml 指纹计算"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")
        
        fingerprint, source = get_deps_fingerprint(tmp_path)
        
        assert fingerprint is not None
        assert fingerprint.startswith("sha256:")
        assert source == "pyproject.toml"

    def test_fingerprint_requirements_fallback(self, tmp_path):
        """测试 fallback 到 requirements.txt"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("fastapi>=0.100\n")
        
        fingerprint, source = get_deps_fingerprint(tmp_path)
        
        assert fingerprint is not None
        assert fingerprint.startswith("sha256:")
        assert source == "requirements.txt"

    def test_fingerprint_pyproject_priority(self, tmp_path):
        """测试 pyproject.toml 优先级高于 requirements.txt"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("fastapi>=0.100\n")
        
        fingerprint, source = get_deps_fingerprint(tmp_path)
        
        assert source == "pyproject.toml"

    def test_no_deps_file(self, tmp_path):
        """测试没有依赖文件时返回 None"""
        fingerprint, source = get_deps_fingerprint(tmp_path)
        
        assert fingerprint is None
        assert source is None


class TestRuntimeInfo:
    """运行时信息测试"""

    def test_python_version(self):
        """测试 Python 版本获取"""
        version = get_python_version()
        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert version == expected

    def test_platform_info(self):
        """测试平台信息获取"""
        info = get_platform_info()
        assert "-" in info  # 格式为 "os-arch"
        assert info.count("-") >= 1


class TestGetReproMeta:
    """完整 ReproMeta 获取测试"""

    def test_basic_meta(self, tmp_path):
        """测试基本元数据收集"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")
        
        meta = get_repro_meta(tmp_path)
        
        assert isinstance(meta, ReproMeta)
        assert meta.python_version is not None
        assert meta.platform_info is not None
        assert meta.deps_fingerprint is not None
        assert meta.deps_source == "pyproject.toml"

    def test_ci_environment(self, tmp_path):
        """测试 CI 环境下的元数据收集"""
        with patch.dict(os.environ, {
            "GITHUB_SHA": "ci-sha-123",
            "GITHUB_REF_NAME": "main",
        }):
            meta = get_repro_meta(tmp_path)
            
            assert meta.git_sha == "ci-sha-123"
            assert meta.git_branch == "main"


class TestIntegrationWithEvidence:
    """与 Evidence 集成测试"""

    def test_evidence_contains_repro(self, tmp_path):
        """测试 Evidence 包含 repro 字段"""
        from qualityfoundry.governance.tracing.collector import TraceCollector
        
        # 创建 pyproject.toml 以便指纹计算
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")
        
        collector = TraceCollector(
            run_id="test-run-123",
            input_nl="test input",
            artifact_root=tmp_path,
        )
        
        evidence = collector.collect()
        
        assert evidence.repro is not None
        assert isinstance(evidence.repro, ReproMeta)
        assert evidence.repro.python_version is not None
        assert evidence.repro.platform_info is not None
