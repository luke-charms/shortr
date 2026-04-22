import json
from datetime import datetime, timezone

from app.core.redis import get_redis

CLICK_COUNT_KEY = "clicks:count:{slug}"
CLICK_EVENTS_KEY = "clicks:events"


async def increment_click(slug: str):
    redis = await get_redis()
    await redis.incr(CLICK_COUNT_KEY.format(slug=slug))


async def track_click_event(slug: str, ip: str | None, user_agent: str | None):
    redis = await get_redis()

    event = {
        "slug": slug,
        "ip": ip,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await redis.lpush(CLICK_EVENTS_KEY, json.dumps(event))