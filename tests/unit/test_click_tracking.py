from sqlalchemy import select
from app.models.link import Link
from unittest.mock import patch
from app.repositories.link_repo import LinkRepository


async def create_test_link(session, slug: str = "abc123", url: str = "https://example.com"):
    link = Link(
        slug=slug,
        url=url,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link

async def test_click_count_starts_at_zero(db_session):
    link = await create_test_link(db_session)

    assert link.click_count == 0


async def test_click_count_increments(client, db_session):
    slug = "abc123_inc"

    await create_test_link(db_session, slug=slug)

    await client.get(f"/{slug}")
    await client.get(f"/{slug}")

    result = await db_session.execute(
        select(Link.click_count).where(Link.slug == slug)
    )
    click_count = result.scalar_one()

    assert click_count == 2

async def test_increment_click_count_noop_when_missing(db_session):

    repo = LinkRepository(db_session)

    # Should not crash
    await repo.increment_click_count("does-not-exist")

""""""

from sqlalchemy.exc import IntegrityError

@patch("app.repositories.link_repo.LinkRepository.create")
async def test_create_link_hits_retry(mock_create, client):
    # First 4 attempts fail
    mock_create.side_effect = [
        IntegrityError("", "", ""),
        IntegrityError("", "", ""),
        IntegrityError("", "", ""),
        IntegrityError("", "", ""),
        # Final attempt succeeds
        type("MockLink", (), {"url": "https://example.com", "slug": "ok123"})()
    ]

    response = await client.post(
        "/api/v1/links",
        json={"url": "https://example.com"}
    )

    assert response.status_code == 201

@patch("app.repositories.link_repo.LinkRepository.create")
async def test_create_link_max_retries_failure(mock_create, client):
    from sqlalchemy.exc import IntegrityError

    mock_create.side_effect = IntegrityError("", "", "")

    response = await client.post(
        "/api/v1/links",
        json={"url": "https://example.com"}
    )

    assert response.status_code == 500
    assert "max retries" in response.json()["detail"]
