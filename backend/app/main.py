from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.redis import init_redis, close_redis, redis_client
from app.core.security import SECURITY_HEADERS
from app.database import close_db
from app.api.v1.health import router as health_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.adsets import router as adsets_router
from app.api.v1.ads import router as ads_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.auth import router as auth_router
from app.api.v1.ws import router as ws_router
from app.api.v1.meta import router as meta_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.reports import router as reports_router
from app.api.v1.users import router as users_router
from app.api.v1.automation import router as automation_router
from app.api.v1.system import router as system_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.billing import router as billing_router
from app.api.v1.branding import router as branding_router
from app.api.v1.security import router as security_router
from app.api.v1.webhooks import router as webhooks_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    setup_logging()
    logger.info("metamind_api_starting", version=settings.VERSION, env=settings.ENVIRONMENT)
    await init_redis()
    yield
    # Graceful Shutdown logic
    logger.info("metamind_api_shutting_down")
    await close_redis()
    await close_db()
    logger.info("metamind_api_shutdown_complete")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Meta Marketing API Management SaaS Backend",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enterprise Security Headers Middleware
@app.middleware("http")
async def add_security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    for header_key, header_val in SECURITY_HEADERS.items():
        response.headers[header_key] = header_val
    return response

# Redis Rate Limiting Middleware (120 requests/minute per client IP)
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    if request.url.path in ["/health", f"{settings.API_V1_STR}/health", "/docs", "/redoc", f"{settings.API_V1_STR}/openapi.json"]:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"rate_limit:{client_ip}:{int(time.time() // 60)}"

    if redis_client:
        try:
            current_count = await redis_client.incr(rate_key)
            if current_count == 1:
                await redis_client.expire(rate_key, 60)
            if current_count > 120:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded. Maximum 120 requests per minute allowed."}
                )
        except Exception as e:
            logger.warning("rate_limit_redis_error", error=str(e))

    return await call_next(request)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 Routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(campaigns_router, prefix=settings.API_V1_STR)
app.include_router(adsets_router, prefix=settings.API_V1_STR)
app.include_router(ads_router, prefix=settings.API_V1_STR)
app.include_router(metrics_router, prefix=settings.API_V1_STR)
app.include_router(copilot_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix=settings.API_V1_STR)
app.include_router(meta_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(automation_router, prefix=settings.API_V1_STR)
app.include_router(system_router, prefix=settings.API_V1_STR)
app.include_router(tenants_router, prefix=settings.API_V1_STR)
app.include_router(billing_router, prefix=settings.API_V1_STR)
app.include_router(branding_router, prefix=settings.API_V1_STR)
app.include_router(security_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)



@app.get("/")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
