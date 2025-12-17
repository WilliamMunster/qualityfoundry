from fastapi import FastAPI
from qualityfoundry.api.v1.routes import router as v1_router

app = FastAPI()
app.include_router(v1_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
