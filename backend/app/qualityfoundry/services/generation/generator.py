from __future__ import annotations

import uuid
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

def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def generate_bundle(req: RequirementInput) -> CaseBundle:
    """MVP generator (deterministic, no LLM).

    Replace this later with:
    - LLM provider adapter (OpenAI/DeepSeek/etc.)
    - JSON-only outputs validated by Pydantic
    - Optional RAG injection (Qdrant) for business rules/risks/components
    """
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
