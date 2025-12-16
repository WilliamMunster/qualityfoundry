from qualityfoundry.services.compile.compiler import compile_step_to_actions


def test_compile_goto():
    actions, warnings = compile_step_to_actions("打开 https://example.com", 15000)
    assert actions and actions[0]["type"] == "goto"
    assert not warnings


def test_compile_assert_text():
    actions, warnings = compile_step_to_actions('应看到 "Example Domain"', 15000)
    assert actions and actions[0]["type"] == "assert_text"
    assert not warnings
