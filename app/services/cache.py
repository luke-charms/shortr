from app.core.redis import get_redis

# TTL constants — centralised so they can be imported by tests
DEFAULT_TTL = 3600  # 1 hour


async def get_url(slug: str) -> str | None:
    """
    Look up a slug in Redis.
    Returns the original URL string, or None on a cache miss.
    """
    return await get_redis().get(slug)

    """
    val = await get_redis().get(slug)
    if val:
        return val.decode("utf-8") if isinstance(val, bytes) else val
    return None
    """

async def set_url(slug: str, url: str, ttl: int = DEFAULT_TTL) -> None:
    """
    Store a slug → URL mapping in Redis with a TTL.
    Silently no-ops if Redis is unavailable (fail-open strategy).
    """
    await get_redis().set(slug, url, ex=ttl)


async def delete_url(slug: str) -> None:
    """
    Remove a slug from the cache.
    Called when a link is deleted so stale redirects stop immediately.
    """
    await get_redis().delete(slug)