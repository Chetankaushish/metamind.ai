import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import logger

redis_client: redis.Redis = None

async def init_redis():
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("redis_connected", host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        redis_client = None

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("redis_connection_closed")

async def check_redis_health() -> bool:
    if not redis_client:
        return False
    try:
        return await redis_client.ping()
    except Exception:
        return False

async def get_redis():
    """
    Return the active Redis client.
    Initialize it if it has not been initialized yet.
    """
    global redis_client

    if redis_client is None:
        await init_redis()

    return redis_client