from fastapi import APIRouter
from qualityfoundry.models.schemas import ExecutionRequest, ExecutionResult
from qualityfoundry.services.execution.executor import execute

router = APIRouter()

@router.post("/execute", response_model=ExecutionResult)
def run(req: ExecutionRequest) -> ExecutionResult:
    return execute(req)
