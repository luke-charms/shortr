from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/shortr"
)


engine = create_async_engine(
    DATABASE_URL, 
    echo=True, 
    pool_pre_ping=True
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)