"""
Unit tests for app/workers/analytics_worker.py

Tests the flush functions in isolation using mocked Redis and DB sessions.
No real Redis or Postgres required.
"""
import json
import pytest, asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call


def make_mock_redis(keys=None, get_values=None, rpop_values=None):
    """Build a mock Redis client with configurable return values."""
    redis = MagicMock()
    redis.keys = AsyncMock(return_value=keys or [])
    redis.get = AsyncMock(side_effect=get_values or [])
    redis.delete = AsyncMock(return_value=1)
    redis.rpop = AsyncMock(side_effect=rpop_values or [None])
    return redis


def make_mock_link(id=1, slug="test", click_count=0):
    link = MagicMock()
    link.id = id
    link.slug = slug
    link.click_count = click_count
    return link


async def test_flush_click_counts_noop_when_no_keys():
    """When there are no click counter keys in Redis, nothing touches the DB."""
    mock_redis = make_mock_redis(keys=[])

    with patch("app.workers.analytics_worker.get_redis", return_value=mock_redis):
        from app.workers.analytics_worker import flush_click_counts
        await flush_click_counts()

    mock_redis.get.assert_not_called()


async def test_flush_click_counts_increments_link_and_deletes_key():
    """
    When a counter key exists, click_count must be incremented by that amount
    and the Redis key must be deleted.
    """
    mock_redis = make_mock_redis(
        keys=["clicks:count:abc123"],
        get_values=["5"],
    )

    mock_link = make_mock_link(slug="abc123", click_count=0)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_link

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_begin)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_db.begin = MagicMock(return_value=mock_begin)

    with patch("app.workers.analytics_worker.get_redis", return_value=mock_redis), \
         patch("app.workers.analytics_worker.AsyncSessionLocal", return_value=mock_db):
        from app.workers.analytics_worker import flush_click_counts
        await flush_click_counts()

    assert mock_link.click_count == 5
    mock_redis.delete.assert_called_once_with("clicks:count:abc123")


async def test_flush_click_counts_skips_zero_counts():
    """A key with value 0 must not touch the DB or attempt a delete."""
    mock_redis = make_mock_redis(
        keys=["clicks:count:abc123"],
        get_values=["0"],
    )

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_begin)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_db.begin = MagicMock(return_value=mock_begin)
    mock_db.execute = AsyncMock()

    with patch("app.workers.analytics_worker.get_redis", return_value=mock_redis), \
         patch("app.workers.analytics_worker.AsyncSessionLocal", return_value=mock_db):
        from app.workers.analytics_worker import flush_click_counts
        await flush_click_counts()

    mock_redis.delete.assert_not_called()


async def test_flush_click_events_noop_on_empty_list():
    """When rpop returns None immediately, no DB operations run."""
    mock_redis = make_mock_redis(rpop_values=[None])

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_begin)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_db.begin = MagicMock(return_value=mock_begin)
    mock_db.execute = AsyncMock()
    mock_db.add = MagicMock()

    with patch("app.workers.analytics_worker.get_redis", return_value=mock_redis), \
         patch("app.workers.analytics_worker.AsyncSessionLocal", return_value=mock_db):
        from app.workers.analytics_worker import flush_click_events
        await flush_click_events()

    mock_db.add.assert_not_called()


async def test_flush_click_events_inserts_click_event():
    """A valid event in the Redis LIST must be inserted as a ClickEvent row."""
    event = json.dumps({
        "slug": "abc123",
        "ip": "1.2.3.4",
        "user_agent": "Mozilla/5.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    mock_redis = make_mock_redis(rpop_values=[event, None])

    mock_link = make_mock_link(id=42, slug="abc123")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_link

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_begin)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_db.begin = MagicMock(return_value=mock_begin)

    with patch("app.workers.analytics_worker.get_redis", return_value=mock_redis), \
         patch("app.workers.analytics_worker.AsyncSessionLocal", return_value=mock_db):
        from app.workers.analytics_worker import flush_click_events
        await flush_click_events()

    mock_db.add.assert_called_once()


async def test_worker_loop_catches_exceptions_and_continues():
    """
    worker_loop must catch exceptions from flush functions and keep running
    rather than crashing the background task.
    """
    call_count = 0
    # Capture the REAL sleep before we patch it
    real_sleep = asyncio.sleep

    async def boom():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("transient error")

    async def fast_sleep(_):
        # Crucial: We must yield to the event loop so the test can 
        # actually switch between the test function and the worker task.
        await real_sleep(0)

    # Note: Patching the specific module reference is correct, 
    # but we avoid recursive mocking by using our 'real_sleep' reference.
    with patch("app.workers.analytics_worker.flush_click_counts", side_effect=boom), \
         patch("app.workers.analytics_worker.flush_click_events", AsyncMock()), \
         patch("app.workers.analytics_worker.asyncio.sleep", side_effect=fast_sleep):

        from app.workers.analytics_worker import worker_loop

        task = asyncio.create_task(worker_loop())
        
        # Give the event loop enough 'ticks' to run the while loop several times
        for _ in range(10):
            await real_sleep(0)
            
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert call_count >= 3