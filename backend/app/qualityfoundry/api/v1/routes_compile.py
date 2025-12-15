"""
compile
king 
2025/12/16
qualityfoundry
"""
from fastapi import APIRouter
from qualityfoundry.models.schemas import TestCase, ExecutionRequest
from qualityfoundry.services.execution.compiler import compile_case_to_dsl

router = APIRouter()


@router.post("/compile", response_model=ExecutionRequest)
def compile_case(case: TestCase, base_url: str, headless: bool = True) -> ExecutionRequest:
    # base_url/headless 走 Query；case 走 Body
    return compile_case_to_dsl(case=case, base_url=base_url, headless=headless)
