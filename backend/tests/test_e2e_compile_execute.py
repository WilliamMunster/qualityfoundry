"""
End-to-end test: Compile → Execute workflow
测试完整的编译→执行链路
"""
import pytest
from pathlib import Path
from qualityfoundry.services.compile.compiler import compile_step_to_actions
from qualityfoundry.models.schemas import Action, ExecutionRequest
from qualityfoundry.runners.playwright.runner import run_actions


class TestEndToEndCompileExecute:
    """端到端测试：编译 → 执行"""

    def test_login_scenario_compile_to_execute(self, tmp_path: Path):
        """测试完整登录场景：编译 → 执行"""
        # 定义登录场景步骤
        login_steps = [
            "打开 https://example.com",
            "输入用户名admin",
            "输入密码123456",
            "点击登录",
            "看到Example Domain"
        ]
        
        # 步骤1：编译所有步骤
        all_actions = []
        all_warnings = []
        
        for step in login_steps:
            actions, warnings = compile_step_to_actions(step, timeout_ms=10000)
            all_actions.extend(actions)
            all_warnings.extend(warnings)
        
        # 验证编译成功
        assert len(all_actions) == 5, f"Expected 5 actions, got {len(all_actions)}"
        assert len(all_warnings) == 0, f"Unexpected warnings: {all_warnings}"
        
        # 验证编译后的 action 类型
        assert all_actions[0]["type"] == "goto"
        assert all_actions[1]["type"] == "fill"
        assert all_actions[2]["type"] == "fill"
        assert all_actions[3]["type"] == "click"
        assert all_actions[4]["type"] == "assert_text"
        
        print("\n✅ 编译成功:")
        for i, action in enumerate(all_actions):
            print(f"  Step {i}: {action['type']}")

    def test_simple_navigation_e2e(self, tmp_path: Path):
        """测试简单导航场景的端到端流程"""
        # 编译步骤
        step = "打开 https://example.com"
        actions, warnings = compile_step_to_actions(step, timeout_ms=10000)
        
        assert len(actions) == 1
        assert len(warnings) == 0
        assert actions[0]["type"] == "goto"
        
        # 转换为 Action 对象并执行
        action_obj = Action(**actions[0])
        req = ExecutionRequest(
            actions=[action_obj],
            headless=True
        )
        
        # 执行
        ok, evidence = run_actions(req, artifact_dir=tmp_path)
        
        # 验证执行结果
        assert ok is True
        assert len(evidence) == 1
        assert evidence[0].ok is True
        assert evidence[0].screenshot is not None
        assert Path(evidence[0].screenshot).exists()
        
        print("\n✅ 端到端测试通过:")
        print(f"  编译: {step} → {actions[0]['type']}")
        print(f"  执行: ok={ok}, screenshot={evidence[0].screenshot}")

    def test_assert_text_e2e(self, tmp_path: Path):
        """测试文本断言的端到端流程"""
        steps = [
            "打开 https://example.com",
            "看到Example Domain"
        ]
        
        # 编译
        all_actions = []
        for step in steps:
            actions, warnings = compile_step_to_actions(step, timeout_ms=10000)
            all_actions.extend(actions)
            assert len(warnings) == 0
        
        # 转换为 Action 对象
        action_objs = [Action(**a) for a in all_actions]
        req = ExecutionRequest(
            actions=action_objs,
            headless=True
        )
        
        # 执行
        ok, evidence = run_actions(req, artifact_dir=tmp_path)
        
        # 验证
        assert ok is True
        assert len(evidence) == 2
        assert all(e.ok for e in evidence)
        
        print("\n✅ 文本断言端到端测试通过:")
        for i, e in enumerate(evidence):
            print(f"  Step {i}: {e.action.type} - ok={e.ok}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
