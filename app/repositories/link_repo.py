from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.link import Link

class LinkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, url: str, slug: str) -> Link:
        link = Link(url=url, slug=slug)
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_by_slug(self, slug: str) -> Link | None:
        result = await self.db.execute(
            select(Link).where(Link.slug == slug)
        )
        return result.scalar_one_or_none()