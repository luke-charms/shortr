from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.link import Link


class LinkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, url: str, slug: str) -> Link:
        """
        Insert a new Link row and flush to the DB within the current
        transaction. The caller owns commit/rollback.
        Raises IntegrityError on slug collision (unique constraint).
        """
        link = Link(url=url, slug=slug)
        self.db.add(link)
        await self.db.flush()
        return link

    async def get_by_slug(self, slug: str) -> Link | None:
        """Return the Link for a given slug, or None if it doesn't exist."""
        result = await self.db.execute(
            select(Link).where(Link.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def increment_click_count(self, slug: str) -> None:
        """Increases click count for a link in the database"""
        result = await self.db.execute(
            select(Link).where(Link.slug == slug)
        )
        link = result.scalar_one_or_none()

        if link:
            link.click_count += 1
            await self.db.flush()