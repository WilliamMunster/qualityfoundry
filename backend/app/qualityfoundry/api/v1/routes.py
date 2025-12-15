from fastapi import APIRouter
from qualityfoundry.api.v1.routes_generation import router as gen_router
from qualityfoundry.api.v1.routes_execution import router as exec_router
from qualityfoundry.api.v1.routes_compile import router as compile_router
from qualityfoundry.api.v1.routes_compile_bundle import router as compile_bundle_router


router = APIRouter(prefix="/api/v1")
router.include_router(gen_router, tags=["generation"])
router.include_router(exec_router, tags=["execution"])
router.include_router(compile_router, tags=["compile"])
router.include_router(compile_bundle_router, tags=["compile"])

