#!/usr/bin/env python3
"""Run Center E2E Acceptance Test

验收测试：Run Center 主路径
1. 访问 /runs 列表页
2. 点击"开启新运行"
3. 验证表单元素可见
4. 返回列表页
"""

import sys
from playwright.sync_api import sync_playwright, expect


def test_run_center_flow():
    """Run Center E2E 验收测试"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("=" * 60)
        print("Run Center E2E Acceptance Test")
        print("=" * 60)
        
        # Step 1: Navigate to Run List
        print("\n[1] 访问运行列表页 /runs...")
        page.goto("http://localhost:5173/runs")
        page.wait_for_load_state("networkidle")
        
        # Verify page loaded
        title = page.locator("h3").first
        expect(title).to_contain_text("执行中心")
        print("    ✅ 列表页加载成功")
        
        # Take screenshot
        page.screenshot(path="/tmp/run_center_list.png")
        print("    📸 截图保存: /tmp/run_center_list.png")
        
        # Step 2: Click "开启新运行" button
        print("\n[2] 点击'开启新运行'按钮...")
        new_run_btn = page.locator("button:has-text('开启新运行')")
        expect(new_run_btn).to_be_visible()
        new_run_btn.click()
        
        page.wait_for_url("**/runs/new")
        page.wait_for_load_state("networkidle")
        print("    ✅ 跳转到新建运行页")
        
        # Step 3: Verify form elements
        print("\n[3] 验证新建运行表单...")
        
        # NL Input textarea
        nl_input = page.locator("textarea[placeholder*='staging']").first
        expect(nl_input).to_be_visible()
        print("    ✅ 测试意图输入框可见")
        
        # Environment select
        env_select = page.locator(".ant-select").first
        expect(env_select).to_be_visible()
        print("    ✅ 环境选择器可见")
        
        # Submit button
        submit_btn = page.locator("button[type='submit']:has-text('立即启动')")
        expect(submit_btn).to_be_visible()
        print("    ✅ 提交按钮可见")
        
        # Take screenshot
        page.screenshot(path="/tmp/run_center_new.png")
        print("    📸 截图保存: /tmp/run_center_new.png")
        
        # Step 4: Navigate back
        print("\n[4] 返回列表页...")
        back_btn = page.locator("button:has-text('返回列表')")
        expect(back_btn).to_be_visible()
        back_btn.click()
        
        page.wait_for_url("**/runs")
        page.wait_for_load_state("networkidle")
        print("    ✅ 返回列表页成功")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("✅ Run Center E2E Acceptance Test PASSED")
        print("=" * 60)
        print("\n截图位置:")
        print("  - /tmp/run_center_list.png")
        print("  - /tmp/run_center_new.png")
        
        return True


if __name__ == "__main__":
    try:
        success = test_run_center_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
