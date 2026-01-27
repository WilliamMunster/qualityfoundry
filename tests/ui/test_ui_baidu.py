import os
import pytest
from pathlib import Path

# 定义 Playwright 测试，默认在 CI 或未设置 PLAYWRIGHT_E2E 时跳过
# 这样可以保证 CI 任务不会因为缺少浏览器而失败
PLAYWRIGHT_E2E = os.environ.get("PLAYWRIGHT_E2E") == "1"

@pytest.mark.playwright
@pytest.mark.skipif(not PLAYWRIGHT_E2E, reason="PLAYWRIGHT_E2E=1 not set, skipping browser test")
def test_baidu_search():
    """
    一个简单的百度搜索测试，用于演示 Playwright 集成和产物收集。
    """
    # 模拟 Playwright 逻辑（为了在没有浏览器时也能有单元验证效果，这里可以写逻辑）
    # 但真实执行时需要 playwright 库
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright package not installed")

    # 获取 QualityFoundry 注入的产物目录
    # 如果是本地直接跑 pytest，默认为当前目录下的 artifacts
    artifact_dir_str = os.environ.get("QUALITYFOUNDRY_ARTIFACT_DIR")
    if not artifact_dir_str:
        artifact_dir = Path("artifacts/manual_run")
    else:
        artifact_dir = Path(artifact_dir_str)
        
    # 确保 ui 目录存在（这是 scoped collection 的目录之一）
    ui_artifact_dir = artifact_dir / "ui"
    ui_artifact_dir.mkdir(parents=True, exist_ok=True)
    
    screenshot_path = ui_artifact_dir / "baidu_search.png"

    with sync_playwright() as p:
        # 使用 chromium 浏览器
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 访问百度
        page.goto("https://www.baidu.com")
        
        # 搜索 QualityFoundry
        page.fill("#kw", "QualityFoundry")
        page.click("#su")
        
        # 等待加载并截图
        page.wait_for_timeout(2000)
        page.screenshot(path=str(screenshot_path))
        
        browser.close()
        
    assert screenshot_path.exists()
    print(f"Screenshot saved to: {screenshot_path}")
