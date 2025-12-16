"""
routes_compile_bundle
king 
2025/12/16
quality-foundry
"""
from fastapi import APIRouter, HTTPException
from qualityfoundry.models.compile_schemas import CompileBundleRequest, CompileBundleResponse, CompiledCase
from qualityfoundry.services.compile.compiler import compile_step_to_actions

router = APIRouter()


@router.post("/compile_bundle", response_model=CompileBundleResponse)
def compile_bundle(req: CompileBundleRequest) -> CompileBundleResponse:
    compiled: list[CompiledCase] = []
    timeout_ms = req.options.default_timeout_ms

    for c in req.cases:
        actions = []
        warnings = []
        for st in c.steps:
            a, w = compile_step_to_actions(st.step, timeout_ms=timeout_ms)
            actions.extend(a)
            warnings.extend(w)

        if req.options.strict and (len(actions) == 0 or any("无法编译" in x for x in warnings)):
            raise HTTPException(status_code=400, detail={
                "case_id": c.id,
                "title": c.title,
                "errors": warnings or ["编译失败：未生成任何 actions"]
            })

        compiled.append(CompiledCase(case_id=c.id, title=c.title, actions=actions, warnings=warnings))

    return CompileBundleResponse(ok=True, compiled=compiled)
