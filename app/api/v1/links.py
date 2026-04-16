from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.link import LinkCreate, LinkResponse


from app.api.deps import get_db
from app.repositories.link_repo import LinkRepository
from app.services.shortener import generate_slug

router = APIRouter(prefix="/api/v1/links", tags=["links"])

@router.post("", response_model=LinkResponse, status_code=201)
async def create_link(
    payload: LinkCreate, 
    db: AsyncSession = Depends(get_db)
):
    repo = LinkRepository(db)

    while True:
        slug = generate_slug()
        if not await repo.get_by_slug(slug):
            break

    link = await repo.create(url=str(payload.url), slug=slug)

    return link
