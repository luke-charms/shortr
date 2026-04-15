from fastapi import APIRouter, status
from app.services.shortener import generate_slug

router = APIRouter(prefix="/api/v1/links", tags=["links"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_link(payload: dict):
    slug = generate_slug()
    return {"slug": slug}