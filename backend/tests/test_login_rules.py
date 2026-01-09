"""
Test cases for login scenario compilation rules
"""
import pytest
from qualityfoundry.services.compile.compiler import compile_step_to_actions


class TestLoginScenarioRules:
    """测试登录场景的编译规则"""

    def test_input_username_variants(self):
        """测试输入用户名的多种表述"""
        test_cases = [
            "输入用户名admin",
            "输入账号admin",
            "输入账户名admin",
            "填写用户名admin",
            "输入username admin",
        ]
        
        for step in test_cases:
            actions, warnings = compile_step_to_actions(step, timeout_ms=5000)
            assert len(actions) == 1, f"Failed for: {step}"
            assert actions[0]["type"] == "fill", f"Failed for: {step}"
            assert actions[0]["locator"]["value"] == 'input[name="username"]', f"Failed for: {step}"
            assert actions[0]["value"] == "admin", f"Failed for: {step}"
            assert len(warnings) == 0, f"Unexpected warnings for: {step}"

    def test_input_username_with_colon(self):
        """测试带冒号的用户名输入"""
        test_cases = [
            "输入用户名：admin",
            "输入用户名: admin",
            "填写账号：testuser",
        ]
        
        for step in test_cases:
            actions, warnings = compile_step_to_actions(step, timeout_ms=5000)
            assert len(actions) == 1, f"Failed for: {step}"
            assert actions[0]["type"] == "fill", f"Failed for: {step}"

    def test_input_password_variants(self):
        """测试输入密码的多种表述"""
        test_cases = [
            "输入密码123456",
            "填写密码password123",
            "输入口令secret",
            "输入password abc123",
        ]
        
        for step in test_cases:
            actions, warnings = compile_step_to_actions(step, timeout_ms=5000)
            assert len(actions) == 1, f"Failed for: {step}"
            assert actions[0]["type"] == "fill", f"Failed for: {step}"
            assert actions[0]["locator"]["value"] == 'input[type="password"]', f"Failed for: {step}"
            assert len(warnings) == 0, f"Unexpected warnings for: {step}"

    def test_click_login_button_variants(self):
        """测试点击登录按钮的多种表述"""
        test_cases = [
            "点击登录",
            "单击登录",
            "点击登录按钮",
            "点击登入",
            "点击sign in",
            "点击login",
        ]
        
        for step in test_cases:
            actions, warnings = compile_step_to_actions(step, timeout_ms=5000)
            assert len(actions) == 1, f"Failed for: {step}"
            assert actions[0]["type"] == "click", f"Failed for: {step}"
            # 登录按钮使用文本匹配
            assert actions[0]["locator"]["strategy"] == "text", f"Failed for: {step}"
            assert len(warnings) == 0, f"Unexpected warnings for: {step}"

    def test_click_submit_button_variants(self):
        """测试点击提交按钮的多种表述"""
        test_cases = [
            "点击提交",
            "单击提交",
            "点击提交按钮",
            "点击确定",
            "点击确认",
            "点击submit",
        ]
        
        for step in test_cases:
            actions, warnings = compile_step_to_actions(step, timeout_ms=5000)
            assert len(actions) == 1, f"Failed for: {step}"
            assert actions[0]["type"] == "click", f"Failed for: {step}"
            assert actions[0]["locator"]["value"] == 'button[type="submit"]', f"Failed for: {step}"
            assert len(warnings) == 0, f"Unexpected warnings for: {step}"

    def test_complete_login_flow(self):
        """测试完整的登录流程"""
        login_steps = [
            ("打开 https://example.com/login", "goto"),
            ("输入用户名admin", "fill"),
            ("输入密码123456", "fill"),
            ("点击登录", "click"),
            ("看到欢迎", "assert_text"),
        ]
        
        for step_text, expected_type in login_steps:
            actions, warnings = compile_step_to_actions(step_text, timeout_ms=5000)
            assert len(actions) == 1, f"Failed for: {step_text}"
            assert actions[0]["type"] == expected_type, f"Failed for: {step_text}"
            assert len(warnings) == 0, f"Unexpected warnings for: {step_text}"


class TestRulePriority:
    """测试规则优先级"""

    def test_specific_rule_over_generic(self):
        """测试具体规则优先于通用规则"""
        # "输入用户名admin" 应该匹配 B3.1（登录场景），而不是 B3（通用输入）
        actions, warnings = compile_step_to_actions("输入用户名admin", timeout_ms=5000)
        
        assert len(actions) == 1
        assert actions[0]["type"] == "fill"
        # 应该使用 CSS 选择器而不是 placeholder
        assert actions[0]["locator"]["strategy"] == "css"
        assert actions[0]["locator"]["value"] == 'input[name="username"]'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
