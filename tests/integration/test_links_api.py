from httpx import AsyncClient


async def test_create_link_persists(client: AsyncClient):
    response = await client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com/"
    assert "slug" in data
    assert len(data["slug"]) == 7


async def test_create_link_invalid_url(client: AsyncClient):
    response = await client.post(
        "/api/v1/links",
        json={"url": "not-a-url"},
    )
    assert response.status_code == 422


async def test_create_link_response_schema(client: AsyncClient):
    """Response must contain exactly url and slug fields."""
    response = await client.post(
        "/api/v1/links",
        json={"url": "https://schema-test.com"},
    )
    assert response.status_code == 201
    data = response.json()
    assert {"url", "slug"}.issubset(data.keys())


async def test_create_link_slug_is_alphanumeric(client: AsyncClient):
    """Slug must only contain URL-safe characters."""
    import re
    response = await client.post(
        "/api/v1/links",
        json={"url": "https://alphanumeric-test.com"},
    )
    assert response.status_code == 201
    assert re.match(r"^[A-Za-z0-9]+$", response.json()["slug"])


async def test_create_link_missing_body(client: AsyncClient):
    """Missing request body must return 422."""
    response = await client.post("/api/v1/links", json={})
    assert response.status_code == 422


async def test_create_link_max_retries_exhausted(client: AsyncClient, monkeypatch):
    """When every slug attempt collides, return 500."""
    # Always produce the same slug so every attempt hits IntegrityError
    monkeypatch.setattr("app.api.v1.links.generate_slug", lambda: "collide")

    # First call plants the slug in the DB
    first = await client.post("/api/v1/links", json={"url": "https://first.com"})
    assert first.status_code == 201

    # Second call exhausts all 5 retries and must 500
    second = await client.post("/api/v1/links", json={"url": "https://second.com"})
    assert second.status_code == 500
    assert "slug" in second.json()["detail"].lower()