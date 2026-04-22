from sqlalchemy.ext.asyncio import AsyncSession
from app.models.click_event import ClickEvent


class ClickRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(
        self,
        link_id: int,
        ip_address: str | None,
        user_agent: str | None,
    ):
        event = ClickEvent(
            link_id=link_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(event)
        await self.db.flush()