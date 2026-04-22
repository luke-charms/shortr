import time
from app.core.redis import get_redis


RATE_LIMIT = 10  # requests
WINDOW = 60  # seconds


async def is_rate_limited(ip: str) -> bool:
    redis = await get_redis()

    key = f"rate_limit:{ip}"
    current = await redis.incr(key)

    if current == 1:
        await redis.expire(key, WINDOW)

    return current > RATE_LIMIT