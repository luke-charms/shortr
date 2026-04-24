"""
Integration tests for the Redis click buffering pipeline.

These tests verify the full flow:
  redirect → analytics.py pushes to Redis LIST
           → analytics_worker.py flushes to Postgres

Design decisions:
- We call flush_click_counts() and flush_click_events() directly rather
  than waiting for the worker's 5-second sleep. Faster and deterministic.
- The `committed_link` fixture commits a real Link to Postgres using its
  own independent session. This is required because the flush worker opens
  its own AsyncSessionLocal() session — if the link only exists inside
  the test's db_session transaction it's invisible to the worker.
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete

from app.models.link import Link
from app.models.click_event import ClickEvent
from app.services.analytics import CLICK_EVENTS_KEY, CLICK_COUNT_KEY
from app.workers.analytics_worker import flush_click_counts, flush_click_events
from app.db.session import AsyncSessionLocal


@pytest.fixture
async def real_redis(redis_client):
    """Real Redis client, flushed before and after each test."""
    await redis_client.flushdb()
    yield redis_client
    await redis_client.flushdb()


@pytest_asyncio.fixture
async def committed_link():
    """
    Create a Link row in a fully committed transaction so it's visible to
    the worker's independent AsyncSessionLocal() sessions.
    Cleans up both ClickEvents and the Link after the test.
    """
    async with AsyncSessionLocal() as db:
        async with db.begin():
            link = Link(slug="buftest1", url="https://example.com")
            db.add(link)
        # Transaction commits here — row is now visible to all sessions

    yield link

    # Teardown: delete click_events first (FK), then the link
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(
                delete(ClickEvent).where(ClickEvent.link_id == link.id)
            )
            await db.execute(
                delete(Link).where(Link.id == link.id)
            )


async def test_flush_click_events_writes_rows_to_db(committed_link, real_redis):
    """
    Core buffering integration test.

    Push two click events onto the Redis LIST (simulating track_click_event()),
    call flush_click_events(), verify two ClickEvent rows appear in Postgres.
    """
    event1 = json.dumps({
        "slug": committed_link.slug,
        "ip": "1.2.3.4",
        "user_agent": "Mozilla/5.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    event2 = json.dumps({
        "slug": committed_link.slug,
        "ip": "5.6.7.8",
        "user_agent": "curl/7.88",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await real_redis.lpush(CLICK_EVENTS_KEY, event1, event2)

    await flush_click_events()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClickEvent).where(ClickEvent.link_id == committed_link.id)
        )
        rows = result.scalars().all()

    assert len(rows) == 2
    user_agents = {r.user_agent for r in rows}
    assert "Mozilla/5.0" in user_agents
    assert "curl/7.88" in user_agents


async def test_flush_click_events_clears_redis_list(committed_link, real_redis):
    """After flushing, the Redis LIST must be empty."""
    event = json.dumps({
        "slug": committed_link.slug,
        "ip": "1.2.3.4",
        "user_agent": "TestAgent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await real_redis.lpush(CLICK_EVENTS_KEY, event)

    await flush_click_events()

    assert await real_redis.llen(CLICK_EVENTS_KEY) == 0


async def test_flush_click_counts_updates_link_click_count(committed_link, real_redis):
    """
    Set a Redis click counter, flush it, verify click_count in Postgres.
    """
    key = CLICK_COUNT_KEY.format(slug=committed_link.slug)
    await real_redis.set(key, "3")

    await flush_click_counts()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Link.click_count).where(Link.slug == committed_link.slug)
        )
        count = result.scalar_one()

    assert count == 3


async def test_flush_click_counts_deletes_redis_key(committed_link, real_redis):
    """After flushing click counts, the Redis counter key must be deleted."""
    key = CLICK_COUNT_KEY.format(slug=committed_link.slug)
    await real_redis.set(key, "2")

    await flush_click_counts()

    assert await real_redis.get(key) is None


async def test_flush_click_events_is_noop_on_empty_buffer(real_redis):
    """flush_click_events() must not raise when the Redis LIST is empty."""
    await real_redis.delete(CLICK_EVENTS_KEY)
    await flush_click_events(batch_size=10)  # must not raise


async def test_flush_click_events_skips_unknown_slugs(real_redis):
    """Events with a slug that doesn't exist in the DB must be silently dropped."""
    event = json.dumps({
        "slug": "ghost-slug-does-not-exist",
        "ip": "1.1.1.1",
        "user_agent": "Ghost",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await real_redis.lpush(CLICK_EVENTS_KEY, event)

    await flush_click_events()  # must not raise

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ClickEvent))
        rows = result.scalars().all()

    assert len(rows) == 0


async def test_full_pipeline_redirect_to_db(committed_link, real_redis):
    """
    End-to-end pipeline test.

    This is the test the plan specifically requires: verifying that clicks
    buffered in Redis eventually appear in Postgres after a flush.

    Flow:
      1. track_click_event() buffers a click onto the Redis LIST
      2. flush_click_events() drains the buffer into Postgres
      3. ClickEvent row is visible in the DB
    """
    from app.services.analytics import track_click_event

    # Step 1 — buffer a click (exactly what the hot path does)
    await track_click_event(
        slug=committed_link.slug,
        ip="9.9.9.9",
        user_agent="EndToEndTest/1.0",
    )

    # Verify it's in Redis before flushing
    assert await real_redis.llen(CLICK_EVENTS_KEY) == 1

    # Step 2 — flush (exactly what the worker does every 5 seconds)
    await flush_click_events()

    # Step 3 — verify it landed in Postgres
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClickEvent).where(ClickEvent.link_id == committed_link.id)
        )
        rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].user_agent == "EndToEndTest/1.0"
    assert rows[0].ip_address == "9.9.9.9"

    # Redis must now be empty
    assert await real_redis.llen(CLICK_EVENTS_KEY) == 0