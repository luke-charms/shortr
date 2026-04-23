import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_redirect_expired_link_returns_410(client, db_session):
    from app.models.link import Link

    expired_link = Link(
        slug="expired123",
        url="https://example.com",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    db_session.add(expired_link)
    await db_session.flush()   # flush within the open transaction, never commit

    response = await client.get("/expired123", follow_redirects=False)

    assert response.status_code == 410
    assert response.json()["detail"] == "Link expired"


@pytest.mark.asyncio
async def test_redirect_valid_link_not_expired(client, db_session):
    from app.models.link import Link

    valid_link = Link(
        slug="valid123",
        url="https://example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    db_session.add(valid_link)
    await db_session.flush()   # flush within the open transaction, never commit

    response = await client.get("/valid123", follow_redirects=False)

    assert response.status_code == 307


@pytest.mark.asyncio
async def test_expired_link_not_cached(client, db_session):
    from app.models.link import Link
    from app.services.cache import get_url

    slug = "nocache123"

    expired_link = Link(
        slug=slug,
        url="https://example.com",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    db_session.add(expired_link)
    await db_session.flush()   # flush within the open transaction, never commit

    await client.get(f"/{slug}", follow_redirects=False)

    cached = await get_url(slug)

    assert cached is None