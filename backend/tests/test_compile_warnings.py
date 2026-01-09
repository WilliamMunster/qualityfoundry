"""
Test cases for compile warnings structure
"""
import pytest
from qualityfoundry.services.compile.compiler import compile_step_to_actions
from qualityfoundry.models.compile_schemas import CompileWarning


def test_empty_step_warning():
    """测试空步骤返回结构化警告"""
    actions, warnings = compile_step_to_actions("", timeout_ms=5000)
    
    assert len(actions) == 0
    assert len(warnings) == 1
    assert isinstance(warnings[0], CompileWarning)
    assert warnings[0].type == "empty_step"
    assert warnings[0].severity == "error"
    assert warnings[0].message == "步骤为空，无法编译"
    assert warnings[0].suggestion is not None


def test_unsupported_step_warning():
    """测试不支持的步骤返回结构化警告"""
    actions, warnings = compile_step_to_actions("这是一个无法识别的步骤", timeout_ms=5000)
    
    assert len(actions) == 0
    assert len(warnings) == 1
    assert isinstance(warnings[0], CompileWarning)
    assert warnings[0].type == "unsupported_step"
    assert warnings[0].severity == "error"
    assert "无法编译步骤" in warnings[0].message
    assert warnings[0].suggestion is not None


def test_supported_step_no_warnings():
    """测试支持的步骤不返回警告"""
    actions, warnings = compile_step_to_actions("打开 https://example.com", timeout_ms=5000)
    
    assert len(actions) == 1
    assert len(warnings) == 0
    assert actions[0]["type"] == "goto"
    assert actions[0]["url"] == "https://example.com"


def test_warning_structure():
    """测试警告结构包含所有必需字段"""
    _, warnings = compile_step_to_actions("", timeout_ms=5000)
    
    warning = warnings[0]
    assert hasattr(warning, "type")
    assert hasattr(warning, "severity")
    assert hasattr(warning, "message")
    assert hasattr(warning, "suggestion")
    assert hasattr(warning, "step_index")
    assert hasattr(warning, "step_text")


def test_warning_severity_levels():
    """测试警告严重程度级别"""
    _, warnings = compile_step_to_actions("", timeout_ms=5000)
    
    # 空步骤应该是 error 级别
    assert warnings[0].severity in ["error", "warning", "info"]
    assert warnings[0].severity == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
