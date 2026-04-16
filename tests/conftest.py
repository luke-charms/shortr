import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.db.base import Base
from app.db.session import engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/shortr"

@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest-asyncio's default to provide a consistent loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    yield engine
    await engine.dispose()

@pytest.fixture(autouse=True)
async def setup_db(engine):
    # Setup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Teardown: Drop tables
    async with engine.begin() as conn:
        # Use 'begin' to ensure the transaction is handled properly
        await conn.run_sync(Base.metadata.drop_all)