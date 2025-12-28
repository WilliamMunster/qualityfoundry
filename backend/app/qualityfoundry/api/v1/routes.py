from fastapi import APIRouter

from qualityfoundry.api.v1.routes_generation import router as generate_router
from qualityfoundry.api.v1.routes_compile import router as compile_router
from qualityfoundry.api.v1.routes_compile_bundle import router as compile_bundle_router
from qualityfoundry.api.v1.routes_execution import router as execute_router
from qualityfoundry.api.v1.routes_execute_bundle import router as execute_bundle_router
from qualityfoundry.api.v1.routes_runs import router as runs_router

# v1 统一入口：所有 v1 API 都从 /api/v1 开始
router = APIRouter(prefix="/api/v1")

router.include_router(generate_router)
router.include_router(compile_router)
router.include_router(compile_bundle_router)
router.include_router(execute_router)
router.include_router(execute_bundle_router)
router.include_router(runs_router)
