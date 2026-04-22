from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.link_repo import LinkRepository
from app.services.cache import get_url, set_url

router = APIRouter(tags=["redirects"])


@router.get("/{slug}", status_code=307)
async def redirect(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Hot path — must be as fast as possible.

    1. Check Redis cache (sub-millisecond)
    2. Fall back to PostgreSQL on cache miss
    3. Populate cache for future requests
    """
    # ── 0. Click count db bind ─────────────────────────────────────────────
    repo = LinkRepository(db)

    # ── 1. Cache hit ──────────────────────────────────────────────────────
    cached_url = await get_url(slug)
    if cached_url:
        await repo.increment_click_count(slug)
        return RedirectResponse(url=cached_url, status_code=307)

    # ── 2. DB lookup ──────────────────────────────────────────────────────
    repo = LinkRepository(db)
    link = await repo.get_by_slug(slug)

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    await repo.increment_click_count(slug)

    # ── 3. Populate cache so next request is a cache hit ──────────────────
    await set_url(slug, link.url)

    return RedirectResponse(url=link.url, status_code=307)