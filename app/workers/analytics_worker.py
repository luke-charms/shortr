import asyncio
import json

from sqlalchemy import select

from app.core.redis import get_redis
from app.db.session import AsyncSessionLocal   # was wrongly named async_session_maker
from app.models.link import Link
from app.models.click_event import ClickEvent

CLICK_EVENTS_KEY = "clicks:events"
CLICK_COUNT_PREFIX = "clicks:count:"


async def flush_click_counts() -> None:
    """
    Read all per-slug click counters from Redis and add them to
    the click_count column in Postgres, then delete the Redis keys.
    get_redis() is synchronous — do not await it.
    """
    redis = get_redis()   # NOT awaited

    keys = await redis.keys(f"{CLICK_COUNT_PREFIX}*")
    if not keys:
        return

    async with AsyncSessionLocal() as db:
        async with db.begin():
            for key in keys:
                slug = key.split(":")[-1]   # keys are str (decode_responses=True)
                count = int(await redis.get(key) or 0)

                if count == 0:
                    continue

                result = await db.execute(
                    select(Link).where(Link.slug == slug)
                )
                link = result.scalar_one_or_none()

                if link:
                    link.click_count += count

                await redis.delete(key)
            # session.begin() commits automatically on __aexit__ with no exception


async def flush_click_events(batch_size: int = 100) -> None:
    """
    Pop up to batch_size click events from the Redis LIST and insert
    them into the click_events table.
    get_redis() is synchronous — do not await it.
    """
    redis = get_redis()   # NOT awaited

    async with AsyncSessionLocal() as db:
        async with db.begin():
            for _ in range(batch_size):
                raw = await redis.rpop(CLICK_EVENTS_KEY)
                if not raw:
                    break

                event = json.loads(raw)

                # Look up link_id from slug so we can write to click_events
                result = await db.execute(
                    select(Link).where(Link.slug == event["slug"])
                )
                link = result.scalar_one_or_none()
                if not link:
                    continue

                click = ClickEvent(
                    link_id=link.id,
                    ip_address=event.get("ip"),
                    user_agent=event.get("user_agent"),
                )
                db.add(click)


async def worker_loop() -> None:
    """
    Infinite loop run as an asyncio background task from the app lifespan.
    Flushes click counters and events every 5 seconds.
    Exceptions are caught and logged so a transient error never kills the worker.
    """
    while True:
        try:
            await flush_click_counts()
            await flush_click_events()
        except Exception as exc:
            print(f"analytics worker error: {exc}")

        await asyncio.sleep(5)