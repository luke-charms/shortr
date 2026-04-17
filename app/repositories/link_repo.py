from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.link import Link
from sqlalchemy.exc import IntegrityError

class LinkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, url: str, slug: str) -> Link:
        link = Link(url=url, slug=slug)
        self.db.add(link)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise

        await self.db.refresh(link)
        return link

    async def get_by_slug(self, slug: str) -> Link | None:
        result = await self.db.execute(
            select(Link).where(Link.slug == slug)
        )
        return result.scalar_one_or_none()




    
