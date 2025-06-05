"""Redis connection and management."""
import redis.asyncio as redis
from app.core.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=settings.redis_decode_responses,
    max_connections=settings.redis_max_connections,
)


async def get_redis() -> redis.Redis:
    """
    Get Redis client instance.
    
    Returns:
        redis.Redis: Redis client
    """
    return redis.Redis(connection_pool=redis_pool)