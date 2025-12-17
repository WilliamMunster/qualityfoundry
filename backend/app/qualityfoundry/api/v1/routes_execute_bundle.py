from __future__ import annotations

from fastapi import APIRouter

from qualityfoundry.models.schemas import ExecuteBundleRequest, ExecuteBundleResponse
from qualityfoundry.services.execution.execute_bundle import execute_bundle

router = APIRouter()


@router.post("/execute_bundle", response_model=ExecuteBundleResponse)
def run_execute_bundle(req: ExecuteBundleRequest) -> ExecuteBundleResponse:
    """一键：bundle -> compile -> execute"""
    return execute_bundle(req)
