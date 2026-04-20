"""
Unit tests for app/repositories/link_repo.py

Tests the repository layer in isolation using a mock AsyncSession.
No database required.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.link_repo import LinkRepository
from app.models.link import Link


@pytest.fixture
def mock_db():
    db = MagicMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


async def test_create_adds_link_and_flushes(mock_db):
    """create() must add the link to the session and call flush()."""
    repo = LinkRepository(mock_db)

    link = await repo.create(url="https://example.com", slug="abc1234")

    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert isinstance(link, Link)
    assert link.url == "https://example.com"
    assert link.slug == "abc1234"


async def test_create_returns_link_with_correct_fields(mock_db):
    """create() must return a Link ORM object with url and slug set."""
    repo = LinkRepository(mock_db)

    link = await repo.create(url="https://test.com", slug="xyz9999")

    assert link.url == "https://test.com"
    assert link.slug == "xyz9999"


async def test_get_by_slug_returns_link_when_found(mock_db):
    """get_by_slug() must return the Link when the query finds a row."""
    expected_link = Link(url="https://example.com", slug="abc1234")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_link
    mock_db.execute.return_value = mock_result

    repo = LinkRepository(mock_db)
    result = await repo.get_by_slug("abc1234")

    assert result is expected_link
    mock_db.execute.assert_called_once()
    mock_result.scalar_one_or_none.assert_called_once()


async def test_get_by_slug_returns_none_when_not_found(mock_db):
    """get_by_slug() must return None when no row matches."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    repo = LinkRepository(mock_db)
    result = await repo.get_by_slug("missing")

    assert result is None