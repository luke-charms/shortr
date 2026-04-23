from app.core.redis import get_redis

RATE_LIMIT = 10  # requests per window
WINDOW = 60      # seconds


async def is_rate_limited(ip: str) -> bool:
    """
    Sliding window rate limiter using Redis INCR + EXPIRE.

    Returns True if the IP has exceeded RATE_LIMIT requests within WINDOW seconds.
    get_redis() is synchronous — do not await it.
    """
    redis = get_redis()

    key = f"rate_limit:{ip}"
    current = await redis.incr(key)

    if current == 1:
        # First request in this window — set the expiry
        await redis.expire(key, WINDOW)

    return current > RATE_LIMIT