"""
Unit tests for app/core/redis.py

Tests the lazy initialisation pattern and shutdown behaviour
without connecting to a real Redis server.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import app.core.redis as redis_module
from app.core.redis import get_redis, close_redis


@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """Reset the module-level _redis singleton before and after each test."""
    redis_module._redis = None
    yield
    redis_module._redis = None


def test_get_redis_creates_client_on_first_call():
    """get_redis() must return a Redis instance when called with no prior state."""
    with patch("app.core.redis.Redis.from_url") as mock_from_url:
        mock_from_url.return_value = MagicMock()
        client = get_redis()
        assert client is not None
        mock_from_url.assert_called_once()


def test_get_redis_returns_same_instance_on_second_call():
    """get_redis() must be a singleton — same object returned every time."""
    with patch("app.core.redis.Redis.from_url") as mock_from_url:
        mock_from_url.return_value = MagicMock()
        client1 = get_redis()
        client2 = get_redis()
        assert client1 is client2
        mock_from_url.assert_called_once()  # only created once


def test_get_redis_uses_redis_url_env_var(monkeypatch):
    """get_redis() must read REDIS_URL from the environment."""
    monkeypatch.setenv("REDIS_URL", "redis://custom-host:1234/2")
    with patch("app.core.redis.Redis.from_url") as mock_from_url:
        mock_from_url.return_value = MagicMock()
        get_redis()
        mock_from_url.assert_called_once_with(
            "redis://custom-host:1234/2",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )


def test_get_redis_uses_default_url_when_env_not_set(monkeypatch):
    """get_redis() must fall back to localhost when REDIS_URL is not set."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    with patch("app.core.redis.Redis.from_url") as mock_from_url:
        mock_from_url.return_value = MagicMock()
        get_redis()
        call_args = mock_from_url.call_args[0][0]
        assert "localhost" in call_args


async def test_close_redis_calls_aclose_and_resets_singleton():
    """close_redis() must close the connection and set _redis back to None."""
    mock_client = MagicMock()
    mock_client.aclose = AsyncMock()
    redis_module._redis = mock_client

    await close_redis()

    mock_client.aclose.assert_called_once()
    assert redis_module._redis is None


async def test_close_redis_is_safe_when_never_initialised():
    """close_redis() must not raise if get_redis() was never called."""
    redis_module._redis = None
    await close_redis()  # must not raise