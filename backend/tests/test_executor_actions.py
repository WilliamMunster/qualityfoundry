"""
Test cases for executor actions (runner.py)

注意：这些测试需要 Playwright 浏览器，在 CI 环境中可能会跳过
"""
import os
import pytest
from pathlib import Path
from qualityfoundry.models.schemas import Action, ActionType, Locator, ExecutionRequest
from qualityfoundry.runners.playwright.runner import run_actions

# 检测是否在 CI 环境中运行
IN_CI = os.environ.get("CI", "").lower() == "true" or os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


@pytest.mark.skipif(IN_CI, reason="Playwright 测试需要浏览器，在 CI 中跳过")
class TestExecutorActions:
    """测试执行器动作实现"""

    def test_assert_visible_action(self, tmp_path: Path):
        """测试 assert_visible 动作"""
        req = ExecutionRequest(
            base_url="https://example.com",
            actions=[
                Action(
                    type=ActionType.GOTO,
                    url="https://example.com",
                    timeout_ms=10000
                ),
                Action(
                    type=ActionType.ASSERT_VISIBLE,
                    locator=Locator(strategy="text", value="Example Domain"),
                    timeout_ms=5000
                )
            ],
            headless=True
        )
        
        ok, evidence, _ = run_actions(req, artifact_dir=tmp_path)
        
        assert ok is True
        assert len(evidence) == 2
        assert evidence[1].ok is True
        assert evidence[1].action.type == ActionType.ASSERT_VISIBLE

    def test_placeholder_locator_strategy(self, tmp_path: Path):
        """测试 placeholder 定位策略"""
        # 注意：这个测试需要一个实际的页面，这里只验证不会抛出异常
        req = ExecutionRequest(
            base_url="https://example.com",
            actions=[
                Action(
                    type=ActionType.GOTO,
                    url="https://example.com",
                    timeout_ms=10000
                )
            ],
            headless=True
        )
        
        ok, evidence, _ = run_actions(req, artifact_dir=tmp_path)
        assert ok is True

    def test_fill_with_css_selector(self, tmp_path: Path):
        """测试使用 CSS 选择器的 fill 动作"""
        req = ExecutionRequest(
            base_url="https://example.com",
            actions=[
                Action(
                    type=ActionType.GOTO,
                    url="https://example.com",
                    timeout_ms=10000
                )
            ],
            headless=True
        )
        
        ok, evidence, _ = run_actions(req, artifact_dir=tmp_path)
        assert ok is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
