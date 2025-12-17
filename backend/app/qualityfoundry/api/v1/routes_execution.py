from fastapi import APIRouter
from qualityfoundry.models.schemas import ExecutionRequest, ExecutionResponse
from qualityfoundry.services.execution.executor import execute

router = APIRouter()


@router.post("/execute", response_model=ExecutionResponse)
def run(req: ExecutionRequest) -> ExecutionResponse:
    return execute(req)
