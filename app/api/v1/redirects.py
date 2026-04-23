from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.api.deps import get_db
from app.repositories.link_repo import LinkRepository
from app.services.cache import get_url, set_url
from app.services.rate_limiter import is_rate_limited
from app.core.logging import logger
from app.services.analytics import increment_click, track_click_event

router = APIRouter(tags=["redirects"])


@router.get("/{slug}", status_code=307)
async def redirect(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Production-grade redirect flow:

    1. Rate limit check (always first)
    2. Try Redis cache (fast path — no DB read)
    3. DB lookup on cache miss
    4. Record analytics via Redis buffer (both paths, consistently)
    5. Return 307 redirect
    """
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    # ── 1. Rate limiting ──────────────────────────────────────────────────
    if await is_rate_limited(ip):
        logger.warning("rate_limited", extra={"ip": ip, "slug": slug})
        raise HTTPException(status_code=429, detail="Too many requests")

    # ── 2. Cache hit path ─────────────────────────────────────────────────
    cached_url = await get_url(slug)
    if cached_url:
        logger.info("cache_hit", extra={"slug": slug})

        await increment_click(slug)
        await track_click_event(slug=slug, ip=ip, user_agent=user_agent)

        return RedirectResponse(url=cached_url, status_code=307)

    # ── 3. DB lookup ──────────────────────────────────────────────────────
    repo = LinkRepository(db)
    link = await repo.get_by_slug(slug)

    if not link:
        logger.warning("slug_not_found", extra={"slug": slug})
        raise HTTPException(status_code=404, detail="Link not found")

    # ── 4. Expiry check ───────────────────────────────────────────────────
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Link expired")

    # ── 5. Analytics — same Redis buffer as cache-hit path ────────────────
    await increment_click(slug)
    await track_click_event(slug=slug, ip=ip, user_agent=user_agent)

    # ── 6. Populate cache for future requests ─────────────────────────────
    if not link.expires_at or link.expires_at > datetime.now(timezone.utc):
        await set_url(slug, link.url)

    logger.info("cache_miss_populated", extra={"slug": slug})

    return RedirectResponse(url=link.url, status_code=307)