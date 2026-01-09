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

        # strict 模式：只有 severity="error" 的警告才触发失败
        if req.options.strict and any(w.severity == "error" for w in warnings):
            error_warnings = [w for w in warnings if w.severity == "error"]
            raise HTTPException(status_code=400, detail={
                "case_id": c.id,
                "title": c.title,
                "errors": [
                    {
                        "type": w.type,
                        "message": w.message,
                        "suggestion": w.suggestion,
                        "step_text": w.step_text
                    }
                    for w in error_warnings
                ]
            })

        compiled.append(CompiledCase(case_id=c.id, title=c.title, actions=actions, warnings=warnings))


    return CompileBundleResponse(ok=True, compiled=compiled)
