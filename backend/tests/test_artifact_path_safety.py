"""Tests for Artifact Path Safety (PR-B)

验证 artifact 下载路由的路径安全校验。
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from qualityfoundry.api.v1.routes_artifacts import _safe_resolve


class TestArtifactPathSafety:
    """路径安全校验测试"""

    def test_absolute_path_rejected(self):
        """绝对路径被拒绝"""
        run_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(run_id, "/etc/passwd")
        assert exc_info.value.status_code == 400
        assert "Absolute paths not allowed" in exc_info.value.detail

    def test_windows_absolute_path_rejected(self):
        """Windows 绝对路径被拒绝"""
        run_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(run_id, "\\windows\\system32")
        assert exc_info.value.status_code == 400
        assert "Absolute paths not allowed" in exc_info.value.detail

    def test_path_traversal_rejected(self):
        """路径遍历被拒绝"""
        run_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(run_id, "../../../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "Path traversal not allowed" in exc_info.value.detail

    def test_path_traversal_in_middle_rejected(self):
        """路径中间的遍历被拒绝"""
        run_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(run_id, "tools/../../../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "Path traversal not allowed" in exc_info.value.detail

    def test_windows_path_traversal_rejected(self):
        """Windows 风格路径遍历被拒绝"""
        run_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(run_id, "..\\..\\etc\\passwd")
        assert exc_info.value.status_code == 400
        assert "Path traversal not allowed" in exc_info.value.detail

    def test_valid_relative_path_file_not_found(self):
        """合法相对路径但文件不存在返回 404"""
        run_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(run_id, "tools/run_pytest/junit.xml")
        assert exc_info.value.status_code == 404
        assert "Artifact not found" in exc_info.value.detail

    def test_single_dot_allowed(self):
        """单点路径组件是允许的（但文件不存在）"""
        run_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(run_id, "./evidence.json")
        # 不应该被 traversal 规则拦截，而是文件不存在
        assert exc_info.value.status_code == 404
