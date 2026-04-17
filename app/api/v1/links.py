from fastapi import APIRouter, Depends, HTTPException
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

    for _ in range(5):
        slug = generate_slug()

        try:
            link = await repo.create(url=str(payload.url), slug=slug)
            #return link
            return LinkResponse(url=link.url, slug=link.slug)
        except:
            continue

    raise HTTPException(status_code=500, detail="Could not generate unique slug")

    

    
