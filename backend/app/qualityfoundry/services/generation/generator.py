from __future__ import annotations

import logging
import re
import uuid
from typing import Optional

from qualityfoundry.models.schemas import (
    RequirementInput,
    TestModule,
    TestObjective,
    TestPoint,
    TestCase,
    TestStep,
    CaseBundle,
    Priority,
)

logger = logging.getLogger(__name__)


def _uid(prefix: str) -> str:
    """生成短 ID，便于前后端/日志定位。"""
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def validate_bundle(bundle: CaseBundle) -> tuple[bool, list[str]]:
    """
    验证生成的 bundle 是否合法
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # 检查必填字段
    if not bundle.requirement:
        errors.append("缺少需求信息")
    
    if not bundle.modules:
        errors.append("缺少模块信息")
    
    if not bundle.cases:
        errors.append("缺少测试用例")
    
    # 检查用例完整性
    for case in bundle.cases:
        if not case.title:
            errors.append(f"用例 {case.id} 缺少标题")
        if not case.steps:
            errors.append(f"用例 {case.id} 缺少测试步骤")
        for i, step in enumerate(case.steps):
            if not step.step:
                errors.append(f"用例 {case.id} 步骤 {i+1} 缺少操作描述")
    
    return len(errors) == 0, errors



def _extract_url_and_expect(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    从需求文本中提取：
    - url: https://example.com
    - expect: Example Domain（用于断言）

    支持：
    - 英文：Open https://... and see XXX.
    - 中文：打开 https://... ，应看到/看到/显示 XXX
    """
    text = text or ""

    # 提取 URL
    m = re.search(r"(https?://\S+)", text)
    url = m.group(1) if m else None

    # 提取期望文本（英文 see）
    expect = None
    m2 = re.search(r"\bsee\s+(.+?)(?:[.。]?$)", text, flags=re.IGNORECASE)
    if m2:
        expect = m2.group(1).strip().strip('"').strip("'")

    # 提取期望文本（中文）
    if not expect:
        m3 = re.search(r"(应看到|看到|显示)\s*(.+)$", text)
        if m3:
            expect = m3.group(2).strip().strip('"').strip("'")

    return url, expect


def _generate_smoke_bundle(req: RequirementInput, url: str, expect: str) -> CaseBundle:
    """
    生成“可稳定执行”的冒烟 bundle：
    - steps 固定为：Open <url> / See <text>
    - 用于 CI/E2E 全链路验证（generate -> compile_bundle -> execute）
    """
    mod = TestModule(
        id=_uid("mod"),
        name="Smoke",
        description="Stable executable smoke bundle (Open URL + See text)",
    )
    obj = TestObjective(
        id=_uid("obj"),
        module_id=mod.id,
        name="Open & See",
        description="Open a URL then assert a visible text",
    )
    tp = TestPoint(
        id=_uid("tp"),
        objective_id=obj.id,
        name="Basic availability",
        tags=["smoke"],
    )
    case = TestCase(
        id=_uid("case"),
        objective_id=obj.id,
        title=f"Open {url} and see '{expect}'",
        preconditions=[],
        data={},
        priority=Priority.P0,
        tags=["smoke", "ui"],
        steps=[
            TestStep(step=f"Open {url}", expected="Page is displayed"),
            TestStep(step=f"See {expect}", expected=f"Text '{expect}' is visible"),
        ],
    )

    return CaseBundle(
        requirement=req,
        modules=[mod],
        objectives=[obj],
        test_points=[tp],
        cases=[case],
    )


def generate_bundle(req: RequirementInput) -> CaseBundle:
    """MVP generator (deterministic, no LLM).

    Replace this later with:
    - LLM provider adapter (OpenAI/DeepSeek/etc.)
    - JSON-only outputs validated by Pydantic
    - Optional RAG injection (Qdrant) for business rules/risks/components
    """

    # ====== 关键：优先走“URL 冒烟分支”（用于 CI 稳定全链路）======
    url, expect = _extract_url_and_expect(req.text)
    if url and expect:
        return _generate_smoke_bundle(req, url=url, expect=expect)

    # ====== 原逻辑：登录模板（fallback，不影响你后续扩展）======
    mod_func = TestModule(
        id=_uid("mod"),
        name="Functional",
        description="Core functional flows derived from requirements",
    )
    mod_risk = TestModule(
        id=_uid("mod"),
        name="Risk & Controls",
        description="Negative/edge/risk scenarios and controls",
    )

    obj_happy = TestObjective(
        id=_uid("obj"),
        module_id=mod_func.id,
        name="Happy path",
        description="Primary user journey",
    )
    obj_negative = TestObjective(
        id=_uid("obj"),
        module_id=mod_risk.id,
        name="Failure handling",
        description="Errors, limits, lockouts, resilience",
    )

    test_points = [
        TestPoint(id=_uid("tp"), objective_id=obj_happy.id, name="Valid login", tags=["happy-path"]),
        TestPoint(id=_uid("tp"), objective_id=obj_negative.id, name="Invalid password", tags=["negative"]),
        TestPoint(id=_uid("tp"), objective_id=obj_negative.id, name="Lock after N failures", tags=["security", "risk"]),
    ]

    cases = [
        TestCase(
            id=_uid("case"),
            objective_id=obj_happy.id,
            title="User can login with valid credentials",
            preconditions=["User account exists", "Login page is reachable"],
            data={"username": "user1", "password": "correct_password"},
            priority=Priority.P0,
            tags=["login", "ui"],
            steps=[
                TestStep(step="Open the login page", expected="Login page is displayed"),
                TestStep(step="Enter valid username and password", expected="Credentials are accepted in the form"),
                TestStep(step="Click the Login button", expected="User is redirected to the home page"),
            ],
        ),
        TestCase(
            id=_uid("case"),
            objective_id=obj_negative.id,
            title="Login fails with invalid password",
            preconditions=["User account exists", "Login page is reachable"],
            data={"username": "user1", "password": "wrong_password"},
            priority=Priority.P1,
            tags=["login", "negative", "ui"],
            steps=[
                TestStep(step="Open the login page", expected="Login page is displayed"),
                TestStep(step="Enter username and an invalid password", expected="Credentials are accepted in the form"),
                TestStep(step="Click the Login button", expected="An error message is displayed and user stays on login page"),
            ],
        ),
    ]

    return CaseBundle(
        requirement=req,
        modules=[mod_func, mod_risk],
        objectives=[obj_happy, obj_negative],
        test_points=test_points,
        cases=cases,
    )
