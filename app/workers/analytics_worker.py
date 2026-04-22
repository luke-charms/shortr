import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import async_session_maker
from app.models.link import Link
from sqlalchemy import select

CLICK_EVENTS_KEY = "clicks:events"
CLICK_COUNT_PREFIX = "clicks:count:"


async def flush_click_counts():
    redis = await get_redis()

    keys = await redis.keys(f"{CLICK_COUNT_PREFIX}*")

    if not keys:
        return

    async with async_session_maker() as db:
        for key in keys:
            slug = key.decode().split(":")[-1]
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

        await db.commit()


async def flush_click_events(batch_size: int = 100):
    redis = await get_redis()

    async with async_session_maker() as db:
        for _ in range(batch_size):
            raw = await redis.rpop(CLICK_EVENTS_KEY)
            if not raw:
                break

            event = json.loads(raw)

            # TODO: insert into ClickEvent table
            # await db.execute(insert(...))

        await db.commit()


async def worker_loop():
    while True:
        try:
            await flush_click_counts()
            await flush_click_events()
        except Exception as e:
            print(f"Worker error: {e}")

        await asyncio.sleep(5)  # tune this


if __name__ == "__main__":
    asyncio.run(worker_loop())