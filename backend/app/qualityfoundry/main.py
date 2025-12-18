from fastapi import FastAPI
from qualityfoundry.api.v1.routes import router as v1_router

app = FastAPI()
app.include_router(v1_router)


@app.get("/health", tags=["health"])
def health():
    return {"ok": True, "service": "qualityfoundry"}