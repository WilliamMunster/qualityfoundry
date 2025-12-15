from fastapi import FastAPI
from qualityfoundry.api.v1.routes import router as v1_router
from qualityfoundry.core.db import init_db

def create_app() -> FastAPI:
    app = FastAPI(title="QualityFoundry API", version="0.1.0")
    init_db()
    app.include_router(v1_router)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app

app = create_app()
