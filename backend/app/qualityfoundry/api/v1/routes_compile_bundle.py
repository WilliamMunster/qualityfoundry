"""
routes_compile_bundle
king 
2025/12/16
qualityfoundry
"""
from fastapi import APIRouter, Query
from qualityfoundry.models.schemas import CaseBundle, ExecutionRequest
from qualityfoundry.services.execution.compiler import compile_case_to_dsl

router = APIRouter()


@router.post("/compile_bundle", response_model=ExecutionRequest)
def compile_bundle(
        bundle: CaseBundle,
        base_url: str = Query(..., description="Target system base URL"),
        headless: bool = Query(True),
        case_index: int = Query(0, ge=0, description="Index in bundle.cases[]"),
) -> ExecutionRequest:
    case = bundle.cases[case_index]
    return compile_case_to_dsl(case=case, base_url=base_url, headless=headless)
