from app.core.redis import redis


async def get_url(slug: str) -> str | None:
    return await redis.get(slug)


async def set_url(slug: str, url: str, ttl: int = 3600) -> None:
    await redis.set(slug, url, ex=ttl)