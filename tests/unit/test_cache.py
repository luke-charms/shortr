"""
Unit tests for app/services/cache.py

All Redis calls are mocked — no running Redis required.
We patch get_redis() to return a mock Redis client, then verify
that our cache functions call the right Redis commands with the
right arguments.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.services.cache import get_url, set_url, delete_url, DEFAULT_TTL


@pytest.fixture
def mock_redis():
    """Return a mock Redis client wired into get_redis()."""
    redis = MagicMock()
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    with patch("app.services.cache.get_redis", return_value=redis):
        yield redis


async def test_get_url_returns_cached_value(mock_redis):
    """get_url must return whatever Redis gives back."""
    mock_redis.get.return_value = "https://example.com"

    result = await get_url("abc1234")

    assert result == "https://example.com"
    mock_redis.get.assert_called_once_with("abc1234")


async def test_get_url_returns_none_on_cache_miss(mock_redis):
    """get_url must return None when Redis returns None (cache miss)."""
    mock_redis.get.return_value = None

    result = await get_url("missing")

    assert result is None


async def test_set_url_calls_redis_set_with_ttl(mock_redis):
    """set_url must call Redis SET with the slug, URL, and default TTL."""
    await set_url("abc1234", "https://example.com")

    mock_redis.set.assert_called_once_with(
        "abc1234", "https://example.com", ex=DEFAULT_TTL
    )

async def test_set_url_accepts_custom_ttl(mock_redis):
    """set_url must pass through a custom TTL value."""
    await set_url("abc1234", "https://example.com", ttl=60)

    mock_redis.set.assert_called_once_with("abc1234", "https://example.com", ex=60)


async def test_delete_url_calls_redis_delete(mock_redis):
    """delete_url must call Redis DELETE with the slug."""
    await delete_url("abc1234")

    mock_redis.delete.assert_called_once_with("abc1234")

@pytest.mark.asyncio
async def test_cache_ttl_expires_integration(redis_client):
    # 1. Set a key with a 1-second expiration
    test_slug = "test-expiry"
    test_url = "https://example.com"
    await set_url(test_slug, test_url, ttl=1)

    # 2. Verify it exists immediately
    val = await get_url(test_slug)
    assert val is not None 

    # 3. Wait for the TTL to pass (1.1s to be safe)
    await asyncio.sleep(1.1)

    # 4. Verify it has expired and returned None
    val_after = await get_url(test_slug)
    assert val_after is None