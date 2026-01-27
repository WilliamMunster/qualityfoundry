from uuid import uuid4
from qualityfoundry.api.v1.routes_orchestrations import _build_tool_request, OrchestrationOptions

def test_playwright_mapping_contract():
    """验证 playwright 工具被正确映射到 run_pytest，并设置默认路径。"""
    run_id = uuid4()
    options = OrchestrationOptions(
        tool_name="playwright",
        args={},  # 空参数
        timeout_s=300
    )
    
    req = _build_tool_request(run_id, "run e2e tests", options)
    
    # 断言映射逻辑
    assert req.tool_name == "run_pytest"
    assert req.args["test_path"] == "tests/ui"
    assert req.timeout_s == 300

def test_playwright_mapping_with_custom_path():
    """验证 playwright 工具在指定路径时保留路径。"""
    run_id = uuid4()
    options = OrchestrationOptions(
        tool_name="playwright",
        args={"test_path": "tests/custom_ui"},
        timeout_s=300
    )
    
    req = _build_tool_request(run_id, "run e2e tests", options)
    
    assert req.tool_name == "run_pytest"
    assert req.args["test_path"] == "tests/custom_ui"

def test_nl_heuristic_fallback():
    """验证 NL 启发式在无 options 时返回默认 pytest。"""
    run_id = uuid4()
    
    # 即使 NL 包含 playwright，在无 options 时也应走默认 pytest (为了安全/确定性)
    req = _build_tool_request(run_id, "run playwright tests", None)
    
    assert req.tool_name == "run_pytest"
    assert req.args["test_path"] == "tests"
