import os
import pytest
from pathlib import Path

# 环境变量：控制是否开启 Playwright UI 测试
PLAYWRIGHT_E2E = os.environ.get("PLAYWRIGHT_E2E") == "1"

@pytest.fixture(scope="session", autouse=True)
def check_playwright_e2e():
    """检查并记录 Playwright 环境状态。"""
    if not PLAYWRIGHT_E2E:
        # 在 CI/本地日志中显式输出，避免误解
        print("\n[SKIP] PLAYWRIGHT_E2E disabled. Browser tests will be skipped.")
    return PLAYWRIGHT_E2E

@pytest.fixture
def qf_artifact_path():
    """返回 QualityFoundry 截图存放的专属目录。
    
    自动识别 QUALITYFOUNDRY_ARTIFACT_DIR 并创建 ui/ 子目录。
    """
    artifact_dir_str = os.environ.get("QUALITYFOUNDRY_ARTIFACT_DIR")
    if not artifact_dir_str:
        # 本地开发模式，默认放在项目根目录 artifacts 下
        artifact_dir = Path("artifacts/manual_run")
    else:
        artifact_dir = Path(artifact_dir_str)
        
    ui_dir = artifact_dir / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    return ui_dir
