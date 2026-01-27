from pathlib import Path
from unittest.mock import MagicMock
from qualityfoundry.tools.runners.pytest_runner import _collect_artifacts
from qualityfoundry.tools.contracts import ArtifactType

def test_collect_artifacts_scoping(tmp_path):
    """验证 _collect_artifacts 只收集允许目录和扩展名的文件。"""
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    
    # 模拟 Context
    ctx = MagicMock()
    ctx.artifact_dir = artifact_dir
    ctx.artifacts = []
    
    def add_artifact(art):
        ctx.artifacts.append(art)
    ctx.add_artifact = add_artifact
    
    # 创建各种文件
    # 1. 允许的目录 + 允许的扩展名
    ui_dir = artifact_dir / "ui"
    ui_dir.mkdir()
    (ui_dir / "screenshot.png").write_text("fake png")
    (ui_dir / "data.json").write_text("{}")
    
    # 2. 允许的根目录文件 (junit.xml)
    (artifact_dir / "junit.xml").write_text("<testsuite></testsuite>")
    
    # 3. 不允许的目录
    secret_dir = artifact_dir / "secrets"
    secret_dir.mkdir()
    (secret_dir / "password.txt").write_text("secret")
    
    # 4. 允许的目录 + 不允许的扩展名
    (ui_dir / "malicious.exe").write_text("virus")
    
    # 执行收集
    _collect_artifacts(ctx, 0)
    
    # 验证收集结果 (将绝对路径转换为相对路径以方便断言)
    art_paths = [str(Path(a.path).relative_to(artifact_dir)) for a in ctx.artifacts]
    
    # 应该包含
    assert "ui/screenshot.png" in art_paths
    assert "ui/data.json" in art_paths
    assert "junit.xml" in art_paths
    
    # 不应该包含
    assert "secrets/password.txt" not in art_paths
    assert "ui/malicious.exe" not in art_paths
    
    # 验证类型
    png_art = next(a for a in ctx.artifacts if "screenshot.png" in a.path)
    assert png_art.type == ArtifactType.SCREENSHOT
    
    json_art = next(a for a in ctx.artifacts if "data.json" in a.path)
    assert json_art.type == ArtifactType.OTHER
    
    junit_art = next(a for a in ctx.artifacts if "junit.xml" in a.path)
    assert junit_art.type == ArtifactType.JUNIT_XML
