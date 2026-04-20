from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.link import LinkCreate, LinkResponse
from app.api.deps import get_db
from app.repositories.link_repo import LinkRepository
from app.services.shortener import generate_slug
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/v1/links", tags=["links"])

@router.post("", response_model=LinkResponse, status_code=201)
async def create_link(
    payload: LinkCreate, 
    db: AsyncSession = Depends(get_db)
):
    repo = LinkRepository(db)
    MAX_RETRIES = 5

    for attempt in range(MAX_RETRIES):
        slug = generate_slug()
        try:
            async with db.begin_nested():
                link = await repo.create(url=str(payload.url), slug=slug)
            
            await db.commit()
            return link
            
        except IntegrityError:
            if attempt == MAX_RETRIES - 1:
                await db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail="Could not generate unique slug"
                )