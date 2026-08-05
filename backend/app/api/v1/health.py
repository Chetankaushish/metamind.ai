from fastapi import APIRouter
from app.schemas.schemas import HealthResponse
from app.database import check_db_health
from app.core.redis import check_redis_health
from app.core.config import settings

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    db_ok = await check_db_health()
    redis_ok = await check_redis_health()
    status = "ok" if (db_ok and redis_ok) else "degraded"
    
    return HealthResponse(
        status=status,
        database=db_ok,
        redis=redis_ok,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT
    )
