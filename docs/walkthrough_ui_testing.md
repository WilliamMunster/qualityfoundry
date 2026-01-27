# 10-Minute Walkthrough: Writing UI Tests (Playwright via Pytest)

This guide shows you how to write and run UI tests that automatically capture screenshots and display them in the QualityFoundry Dashboard.

## 1. Why "Pytest" for Playwright?

You might notice we select **"Pytest (UI: Playwright)"** in the UI instead of a standalone Playwright tool.
> [!TIP]
> **Key Concept**: We use `run_pytest` to execute Playwright scripts. This leverages our existing secure sandbox and artifact collection pipeline while we finalize the dedicated browser sandbox.

## 2. Quick Start: Create your first test

Create a file in `tests/ui/test_my_feature.py`:

```python
import pytest
from playwright.sync_api import Page

@pytest.mark.playwright
def test_login_flow(page: Page, qf_artifact_path):
    # 'qf_artifact_path' fixture is provided in tests/ui/conftest.py
    page.goto("https://example.com/login")
    page.fill("#user", "admin")
    page.click("#submit")
    
    # Capture evidence
    page.screenshot(path=str(qf_artifact_path / "login_success.png"))
    
    assert page.is_visible(".dashboard")
```

## 3. How to Run

### Local Execution (Full UI)
Set `PLAYWRIGHT_E2E=1` to enable browser tests locally:
```bash
PLAYWRIGHT_E2E=1 pytest tests/ui/test_my_feature.py
```

### From Dashboard
1. Go to **New Run**.
2. Select **"Pytest (UI: Playwright)"**.
3. Set **Test Path** to `tests/ui`.
4. Click **Launch**.

## 4. Where is my evidence?

QualityFoundry automatically scans the `ui/` subdirectory of your artifact directory. Any `.png`, `.jpg`, or `.webp` files found there will appear in the **Run Detail** page under the "Evidence" tab.

## 5. Troubleshooting

- **Test Skipped in CI?**: This is intentional. CI environments usually lack browsers. Check the logs for `PLAYWRIGHT_E2E disabled`.
- **Screenshot Missing?**: Ensure you are saving to exactly `qf_artifact_path` (which points to `QUALITYFOUNDRY_ARTIFACT_DIR/ui`).
- **Sandbox Blocked?**: If your test visits a new domain, check the Environment's network policy.
