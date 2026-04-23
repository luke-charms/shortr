import json
from datetime import datetime, timezone

from app.core.redis import get_redis

CLICK_COUNT_KEY = "clicks:count:{slug}"
CLICK_EVENTS_KEY = "clicks:events"


async def increment_click(slug: str) -> None:
    """
    Increment the Redis click counter for a slug.
    get_redis() is synchronous — do not await it.
    """
    redis = get_redis()   # NOT awaited — get_redis() is a plain function
    await redis.incr(CLICK_COUNT_KEY.format(slug=slug))


async def track_click_event(
    slug: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """
    Push a click event dict onto the Redis LIST for later processing.
    get_redis() is synchronous — do not await it.
    """
    redis = get_redis()   # NOT awaited — get_redis() is a plain function

    event = {
        "slug": slug,
        "ip": ip,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await redis.lpush(CLICK_EVENTS_KEY, json.dumps(event))