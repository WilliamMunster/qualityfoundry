"""
routes_execute_bundle
king 
2025/12/16
qualityfoundry
"""
from __future__ import annotations

from fastapi import APIRouter

from qualityfoundry.models.schemas import ExecuteBundleRequest, ExecuteBundleResponse
from qualityfoundry.services.execution.execute_bundle import execute_bundle

router = APIRouter()


@router.post("/execute_bundle", response_model=ExecuteBundleResponse)
def execute_bundle_api(req: ExecuteBundleRequest) -> ExecuteBundleResponse:
    """
    一键执行 Bundle：
    - 服务端内部完成：compile_bundle -> execute
    - 客户端只需传 bundle，无需自己拼 actions
    """
    return execute_bundle(req)
