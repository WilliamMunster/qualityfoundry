# 10 分钟上手指南：编写 UI 测试 (Playwright via Pytest)

本指南将向您展示如何编写和运行 UI 测试，这些测试会自动捕获截图并展示在 QualityFoundry Dashboard 中。

## 1. 为什么 Playwright 要通过 Pytest 运行？

您可能会注意到，我们在 UI 中选择的是 **"Pytest (UI: Playwright)"**，而不是独立的 Playwright 工具。
> [!TIP]
> **核心概念**：我们使用 `run_pytest` 来执行 Playwright 脚本。这可以在我们完善专用浏览器沙箱的同时，复用现有的安全沙箱和产物收集流水线。

## 2. 快速开始：创建您的第一个测试

在 `tests/ui/test_my_feature.py` 中创建一个文件：

```python
import pytest
from playwright.sync_api import Page

@pytest.mark.playwright
def test_login_flow(page: Page, qf_artifact_path):
    # 'qf_artifact_path' fixture 由 tests/ui/conftest.py 提供
    page.goto("https://example.com/login")
    page.fill("#user", "admin")
    page.click("#submit")
    
    # 捕获证据
    page.screenshot(path=str(qf_artifact_path / "login_success.png"))
    
    assert page.is_visible(".dashboard")
```

## 3. 如何运行

### 本地执行 (完整 UI)
设置 `PLAYWRIGHT_E2E=1` 以在本地启用浏览器测试：
```bash
PLAYWRIGHT_E2E=1 pytest tests/ui/test_my_feature.py
```

### 从 Dashboard 运行
1. 进入 **New Run**。
2. 选择 **"Pytest (UI: Playwright)"**。
3. 将 **Test Path** 设置为 `tests/ui`。
4. 点击 **Launch**。

## 4. 我的证据在哪里？

QualityFoundry 会自动扫描产物目录下的 `ui/` 子目录。在该目录下发现的任何 `.png`、`.jpg` 或 `.webp` 文件都将显示在 **Run Detail** 页面的 "Evidence" 标签页中。

## 5. 故障排除

- **测试在 CI 中被跳过？**：这是预期的。CI 环境通常缺少浏览器。检查日志中是否出现 `PLAYWRIGHT_E2E disabled`。
- **截图缺失？**：确保您将其保存到了确切的 `qf_artifact_path` 目录（该目录指向 `QUALITYFOUNDRY_ARTIFACT_DIR/ui`）。
- **沙箱拦截？**：如果您的测试访问了新域名，请检查环境的网络策略。
