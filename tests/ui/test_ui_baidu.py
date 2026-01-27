import pytest
from playwright.sync_api import sync_playwright
from .conftest import PLAYWRIGHT_E2E

@pytest.mark.playwright
@pytest.mark.skipif(not PLAYWRIGHT_E2E, reason="PLAYWRIGHT_E2E=1 not set")
def test_baidu_search(qf_artifact_path):
    """
    百度搜索测试模板。
    使用 qf_artifact_path 自动定位截图目录。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.baidu.com")
        
        # 搜索与截图
        page.fill("#kw", "QualityFoundry")
        page.click("#su")
        page.wait_for_timeout(2000)
        
        screenshot_path = qf_artifact_path / "baidu_search.png"
        page.screenshot(path=str(screenshot_path))
        
        browser.close()
        assert screenshot_path.exists()
