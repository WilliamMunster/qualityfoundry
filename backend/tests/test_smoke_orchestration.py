"""Smoke Tests for Orchestration API (PR-4)

最小闭环验证：
- 调用 /api/v1/orchestrations/run
- 跑本地 pytest fixture（不依赖外网/浏览器）
- 返回 decision + evidence + links
- report_url 可下载 evidence.json
"""

import pytest


@pytest.mark.smoke
def test_orchestration_pass_with_sample_tests(client):
    """
    测试通过场景：跑 sample_tests 全部通过。

    验证：
    - API 返回 200
    - decision 为 PASS
    - evidence 包含测试摘要
    - links.report_url 存在
    """
    resp = client.post(
        "/api/v1/orchestrations/run",
        json={
            "nl_input": "run local sample pytest and generate evidence",
            "options": {
                "tool_name": "run_pytest",
                "args": {
                    "test_path": "tests/fixtures/sample_tests/test_sample.py",
                },
                "timeout_s": 120,
            },
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # 验证响应结构
    assert "run_id" in data
    assert "decision" in data
    assert "reason" in data
    assert "evidence" in data
    assert "links" in data

    # 验证决策（sample_tests 全部通过应为 PASS）
    assert data["decision"] == "PASS", f"Expected PASS, got {data['decision']}: {data['reason']}"

    # 验证 evidence
    evidence = data["evidence"]
    assert isinstance(evidence, dict)
    assert "run_id" in evidence
    assert "summary" in evidence or "tool_calls" in evidence

    # 验证 links
    links = data["links"]
    assert "report_url" in links
    assert links["report_url"] is not None


@pytest.mark.smoke
def test_orchestration_fail_with_failing_tests(client):
    """
    测试失败场景：跑包含失败测试的 fixture。

    验证：
    - API 返回 200（API 调用本身成功）
    - decision 为 FAIL
    - reason 说明失败原因
    """
    resp = client.post(
        "/api/v1/orchestrations/run",
        json={
            "nl_input": "run tests that will fail",
            "options": {
                "tool_name": "run_pytest",
                "args": {
                    "test_path": "tests/fixtures/sample_tests/test_with_failure.py",
                },
                "timeout_s": 120,
            },
        },
    )

    assert resp.status_code == 200
    data = resp.json()

    # 验证决策（有失败测试应为 FAIL）
    assert data["decision"] == "FAIL", f"Expected FAIL, got {data['decision']}: {data['reason']}"
    assert "fail" in data["reason"].lower() or "1" in data["reason"]


@pytest.mark.smoke
def test_orchestration_hitl_with_high_risk_input(client):
    """
    HITL 场景：高危关键词触发人工审核。

    验证：
    - 包含高危关键词（production）的输入触发 NEED_HITL
    - approval_id 可能被创建
    """
    resp = client.post(
        "/api/v1/orchestrations/run",
        json={
            "nl_input": "deploy to production environment",
            "options": {
                "tool_name": "run_pytest",
                "args": {
                    "test_path": "tests/fixtures/sample_tests/test_sample.py",
                },
            },
        },
    )

    assert resp.status_code == 200
    data = resp.json()

    # 验证决策（高危关键词应为 NEED_HITL）
    assert data["decision"] == "NEED_HITL", f"Expected NEED_HITL, got {data['decision']}"
    assert "high-risk" in data["reason"].lower() or "production" in data["reason"].lower()


@pytest.mark.smoke
def test_orchestration_report_url_downloadable(client):
    """
    验证 report_url 可下载。

    流程：
    1. 执行编排
    2. 获取 report_url
    3. 下载 evidence.json
    4. 验证内容
    """
    # 1. 执行编排
    resp = client.post(
        "/api/v1/orchestrations/run",
        json={
            "nl_input": "run tests and check evidence download",
            "options": {
                "tool_name": "run_pytest",
                "args": {
                    "test_path": "tests/fixtures/sample_tests/test_sample.py",
                },
            },
        },
    )

    assert resp.status_code == 200
    data = resp.json()

    # 2. 获取 report_url
    report_url = data["links"]["report_url"]
    assert report_url is not None

    # 3. 下载 evidence.json
    download_resp = client.get(report_url)
    assert download_resp.status_code == 200, f"Failed to download: {download_resp.status_code}"

    # 4. 验证内容
    content_type = download_resp.headers.get("content-type", "")
    assert "application/json" in content_type

    evidence = download_resp.json()
    assert "run_id" in evidence
    assert evidence["run_id"] == data["run_id"]


@pytest.mark.smoke
def test_orchestration_tool_not_found(client):
    """
    工具不存在场景。

    验证：
    - API 返回 200（不是 500）
    - decision 为 FAIL
    - reason 说明工具不存在
    """
    resp = client.post(
        "/api/v1/orchestrations/run",
        json={
            "nl_input": "run nonexistent tool",
            "options": {
                "tool_name": "nonexistent_tool",
                "args": {},
            },
        },
    )

    assert resp.status_code == 200
    data = resp.json()

    # 验证决策
    assert data["decision"] == "FAIL"
    # reason 或 evidence 中应该有关于工具失败的信息


@pytest.mark.smoke
def test_artifacts_path_traversal_blocked(client):
    """
    安全测试：路径遍历攻击被阻止。

    验证：
    - 尝试访问父目录被拒绝
    """
    # 尝试路径遍历
    resp = client.get("/api/v1/artifacts/00000000-0000-0000-0000-000000000000/../../../etc/passwd")
    assert resp.status_code in (400, 404), f"Expected 400 or 404, got {resp.status_code}"


@pytest.mark.smoke
def test_artifacts_nonexistent_run(client):
    """
    测试不存在的运行 ID。

    验证：
    - 返回 404
    """
    resp = client.get("/api/v1/artifacts/00000000-0000-0000-0000-000000000000/evidence.json")
    assert resp.status_code == 404
