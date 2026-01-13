from fastapi import APIRouter

from qualityfoundry.api.v1.routes_generation import router as generate_router
from qualityfoundry.api.v1.routes_compile import router as compile_router
from qualityfoundry.api.v1.routes_compile_bundle import router as compile_bundle_router
from qualityfoundry.api.v1.routes_execution import router as execute_router
from qualityfoundry.api.v1.routes_execute_bundle import router as execute_bundle_router
from qualityfoundry.api.v1.routes_runs import router as runs_router
from qualityfoundry.api.v1.routes_requirements import router as requirements_router
from qualityfoundry.api.v1.routes_upload import router as upload_router
from qualityfoundry.api.v1.routes_approvals import router as approvals_router
from qualityfoundry.api.v1.routes_scenarios import router as scenarios_router
from qualityfoundry.api.v1.routes_testcases import router as testcases_router
from qualityfoundry.api.v1.routes_environments import router as environments_router
from qualityfoundry.api.v1.routes_executions import router as executions_router
from qualityfoundry.api.v1.routes_users import router as users_router
from qualityfoundry.api.v1.routes_ai_configs import router as ai_configs_router
from qualityfoundry.api.v1.routes_reports import router as reports_router
from qualityfoundry.api.v1.routes_config import router as config_router
from qualityfoundry.api.v1.routes_ai_prompts import router as ai_prompts_router
from qualityfoundry.api.v1.routes_websocket import router as websocket_router

# v1 统一入口：所有 v1 API 都从 /api/v1 开始
router = APIRouter(prefix="/api/v1")

router.include_router(generate_router)
router.include_router(compile_router)
router.include_router(compile_bundle_router)
router.include_router(execute_router)
router.include_router(execute_bundle_router)
router.include_router(runs_router)
router.include_router(requirements_router)
router.include_router(upload_router)
router.include_router(approvals_router)
router.include_router(scenarios_router)
router.include_router(testcases_router)
router.include_router(environments_router)
router.include_router(executions_router)
router.include_router(users_router)
router.include_router(ai_configs_router)
router.include_router(reports_router)
router.include_router(config_router)
router.include_router(ai_prompts_router)
router.include_router(websocket_router)

