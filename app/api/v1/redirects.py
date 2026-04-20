from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.link_repo import LinkRepository
from app.services.cache import get_url, set_url

router = APIRouter()

@router.get("/{slug}")
async def redirect(slug: str, db: AsyncSession = Depends(get_db)):
    cached_url = await get_url(slug)
    if cached_url:
        return RedirectResponse(url=cached_url)

    repo = LinkRepository(db)
    link = await repo.get_by_slug(slug)
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    await set_url(slug, link.url)
    
    return RedirectResponse(url=link.url)