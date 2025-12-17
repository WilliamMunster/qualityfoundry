from fastapi import APIRouter
from qualityfoundry.models.schemas import RequirementInput, CaseBundle
from qualityfoundry.services.generation.generator import generate_bundle

router = APIRouter()


@router.post("/generate", response_model=CaseBundle)
def generate(req: RequirementInput) -> CaseBundle:
    return generate_bundle(req)
