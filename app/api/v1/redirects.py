from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.link_repo import LinkRepository
from app.repositories.click_repo import ClickRepository
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

    1. Rate limit (always first)
    2. Try cache (fast path, no DB read)
    3. Fallback to DB
    4. Record analytics (non-blocking candidate)
    5. Return redirect
    """

    ip = request.client.host if request.client else "unknown"

    # ── 1. Rate limiting ────────────────────────────────────────────────
    if await is_rate_limited(ip):
        logger.warning("rate_limited", extra={"ip": ip, "slug": slug})
        raise HTTPException(status_code=429, detail="Too many requests")

    repo = LinkRepository(db)
    click_repo = ClickRepository(db)

    # ── 2. Cache lookup ──────────────────────────────────────
    cached_url = await get_url(slug)
    if cached_url:
        logger.info("cache_hit", extra={"slug": slug})

        # async que click counter increment
        await increment_click(slug)

        # Still writes to DB --> consider async queue later
        #await repo.increment_click_count(slug)

        await track_click_event(
        slug=slug,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )


        return RedirectResponse(url=cached_url, status_code=307)

    # ── 3. DB lookup ────────────────────────────────────────
    link = await repo.get_by_slug(slug)

    if not link:
        logger.warning("slug_not_found", extra={"slug": slug})
        raise HTTPException(status_code=404, detail="Link not found")

    # ── 4. Analytics & tracking ─────────────────────────────────────────
    await repo.increment_click_count(slug)

    await click_repo.create_event(
        link_id=link.id,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )

    # ── 5. Populate cache ───────────────────────────────────────────────
    await set_url(slug, link.url)

    logger.info("cache_miss_populated", extra={"slug": slug})

    return RedirectResponse(url=link.url, status_code=307)