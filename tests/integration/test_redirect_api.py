from httpx import AsyncClient
from unittest.mock import AsyncMock


async def test_redirect_existing_link(client: AsyncClient) -> None:
    """DB miss path: slug not in cache, found in DB, returns 307."""
    create_resp = await client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
    )
    assert create_resp.status_code == 201, create_resp.json()
    slug = create_resp.json()["slug"]

    response = await client.get(f"/{slug}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/"


async def test_redirect_nonexistent_slug_returns_404(client: AsyncClient) -> None:
    """Slug not in cache AND not in DB must return 404."""
    response = await client.get("/doesnotexist", follow_redirects=False)
    assert response.status_code == 404


async def test_redirect_uses_cache(client: AsyncClient, monkeypatch) -> None:
    """Cache hit path: get_url returns a URL, DB is never touched."""
    cached_url = "https://cached-example.com"
    monkeypatch.setattr(
        "app.api.v1.redirects.get_url", AsyncMock(return_value=cached_url)
    )

    response = await client.get("/any-slug", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == cached_url


async def test_redirect_writes_to_cache_after_db_hit(
    client: AsyncClient, monkeypatch
) -> None:
    """After a DB hit, set_url must be called with the correct slug and URL."""
    set_url_mock = AsyncMock()
    monkeypatch.setattr("app.api.v1.redirects.set_url", set_url_mock)

    # Plant a link in the DB
    create_resp = await client.post(
        "/api/v1/links",
        json={"url": "https://cache-write-test.com"},
    )
    slug = create_resp.json()["slug"]

    await client.get(f"/{slug}", follow_redirects=False)

    # set_url must have been called once with the right args
    set_url_mock.assert_called_once_with(slug, "https://cache-write-test.com/")


async def test_create_link_collision_retry(client: AsyncClient, monkeypatch) -> None:
    """Slug collision retries until a unique slug is found."""
    slugs = iter(["dup1", "dup1", "unique1"])
    monkeypatch.setattr("app.api.v1.links.generate_slug", lambda: next(slugs))

    first = await client.post("/api/v1/links", json={"url": "https://first.com"})
    assert first.status_code == 201

    second = await client.post("/api/v1/links", json={"url": "https://second.com"})
    assert second.status_code == 201
    assert second.json()["slug"] == "unique1"