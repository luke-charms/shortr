import pytest
import json
from app.services.analytics import increment_click, track_click_event, CLICK_EVENTS_KEY
from app.services.rate_limiter import is_rate_limited
from app.core.redis import get_redis

@pytest.mark.asyncio
async def test_analytics_increment_and_track():
    redis = get_redis()
    slug = "test-analytics"
    
    # Test increment_click
    await increment_click(slug)
    count = await redis.get(f"clicks:count:{slug}")
    assert int(count) >= 1

    # Test track_click_event
    await track_click_event(slug, "1.2.3.4", "pytest-agent")
    event_json = await redis.lpop(CLICK_EVENTS_KEY)
    event = json.loads(event_json)
    assert event["slug"] == slug
    assert event["ip"] == "1.2.3.4"

@pytest.mark.asyncio
async def test_rate_limiter_full_cycle():
    ip = "192.168.1.1"
    # First hit should not be limited and should set expiry
    limited = await is_rate_limited(ip)
    assert limited is False
    
    # Hit it up to the limit (10)
    for _ in range(9):
        await is_rate_limited(ip)
        
    # The 11th hit should return True
    final_hit = await is_rate_limited(ip)
    assert final_hit is True