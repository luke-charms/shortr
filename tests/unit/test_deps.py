"""
Unit tests for app/api/deps.py

Tests that get_db() yields a valid AsyncSession using the real
session factory (no HTTP layer involved).
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch


async def test_get_db_yields_async_session():
    """get_db() must yield an AsyncSession instance."""
    from app.api.deps import get_db

    mock_session = MagicMock(spec=AsyncSession)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_session)

    with patch("app.api.deps.AsyncSessionLocal", mock_session_factory):
        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session


async def test_get_db_closes_session_after_use():
    """get_db() must close the session (exit the context manager) after yielding."""
    from app.api.deps import get_db

    mock_session = MagicMock(spec=AsyncSession)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.deps.AsyncSessionLocal", return_value=mock_session):
        gen = get_db()
        await gen.__anext__()
        try:
            await gen.aclose()
        except StopAsyncIteration:
            pass

    mock_session.__aexit__.assert_called_once()