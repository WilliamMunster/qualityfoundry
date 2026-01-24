from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from qualityfoundry.api.v1.routes import router as v1_router
from qualityfoundry.logging_config import setup_logging


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # 添加安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com;"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app = FastAPI()

# 配置日志
setup_logging()

# 安全响应头中间件
app.add_middleware(SecurityHeadersMiddleware)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境请指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}


@app.on_event("startup")
def on_startup():
    """应用启动时执行初始化逻辑。
    
    包含：
    - 数据 seed（默认环境等）
    - Token 清理（需开启 QF_TOKEN_CLEANUP_ENABLED=true）
    
    注意：如果数据库不可用（如 CI 环境），不阻塞服务启动。
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from qualityfoundry.database.config import SessionLocal
        from qualityfoundry.services.startup_seeds import run_startup_seeds
        from qualityfoundry.services.auth_service import AuthService
        from qualityfoundry.core.config import settings
        
        db = SessionLocal()
        try:
            # 1. 数据 seed
            run_startup_seeds(db)
            
            # 2. Token 清理（需开启 feature flag）
            if settings.TOKEN_CLEANUP_ENABLED:
                deleted = AuthService.cleanup_expired_tokens(
                    db, 
                    retention_days=settings.TOKEN_CLEANUP_RETENTION_DAYS
                )
                if deleted > 0:
                    logger.info(
                        f"Token 清理完成: 删除 {deleted} 个过期/撤销 token "
                        f"(retention={settings.TOKEN_CLEANUP_RETENTION_DAYS}d)"
                    )
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Startup tasks skipped: {e}")


