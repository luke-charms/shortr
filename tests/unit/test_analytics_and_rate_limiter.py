from sqlalchemy import select
from app.models.link import Link
from unittest.mock import patch
from app.repositories.link_repo import LinkRepository


async def create_test_link(session, slug: str = "abc123", url: str = "https://example.com"):
    link = Link(slug=slug, url=url)
    session.add(link)
    await session.flush()   # flush within the open transaction — never commit
    # No refresh() needed: expire_on_commit=False means the object retains
    # its in-memory state, and flush() has already assigned the DB id
    return link


async def test_click_count_starts_at_zero(db_session):
    link = await create_test_link(db_session)

    assert link.click_count == 0


async def test_click_count_increments(client, db_session):
    """
    Verifies increment_click_count() works correctly via the repository.
    Note: the redirect hot path now buffers clicks in Redis rather than
    writing click_count to DB directly, so we test the repo method directly.
    """
    slug = "abc123_inc"
    link = await create_test_link(db_session, slug=slug)

    repo = LinkRepository(db_session)
    await repo.increment_click_count(slug)
    await repo.increment_click_count(slug)

    result = await db_session.execute(
        select(Link.click_count).where(Link.slug == slug)
    )
    click_count = result.scalar_one()

    assert click_count == 2


async def test_increment_click_count_noop_when_missing(db_session):
    repo = LinkRepository(db_session)

    # Should not crash when slug does not exist
    await repo.increment_click_count("does-not-exist")


from sqlalchemy.exc import IntegrityError


@patch("app.repositories.link_repo.LinkRepository.create")
async def test_create_link_hits_retry(mock_create, client):
    # First 4 attempts fail with collision, 5th succeeds
    mock_create.side_effect = [
        IntegrityError("", "", ""),
        IntegrityError("", "", ""),
        IntegrityError("", "", ""),
        IntegrityError("", "", ""),
        type("MockLink", (), {
            "id": 1,
            "url": "https://example.com",
            "slug": "ok123",
            "click_count": 0,
            "expires_at": None,
        })(),
    ]

    response = await client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 201


@patch("app.repositories.link_repo.LinkRepository.create")
async def test_create_link_max_retries_failure(mock_create, client):
    mock_create.side_effect = IntegrityError("", "", "")

    response = await client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 500
    assert "max retries" in response.json()["detail"]