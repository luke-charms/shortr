import os
from redis.asyncio import Redis

# Redis client is created lazily at first use, not at import time.
# This means tests can run without a Redis server — they patch get_url/set_url
# before the client is ever instantiated.
_redis: Redis | None = None


def get_redis() -> Redis:
    """Return the module-level Redis client, creating it on first call."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis


async def close_redis() -> None:
    """Gracefully close the Redis connection pool. Called on app shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None