import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_redirect_existing_link(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
    )
    assert create_resp.status_code == 201, create_resp.json()
    slug = create_resp.json()["slug"]

    response = await client.get(f"/{slug}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/"

@pytest.mark.asyncio
async def test_redirect_nonexistent_slug_returns_404(client: AsyncClient) -> None:
    response = await client.get("/doesnotexist", follow_redirects=False)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_uses_cache(client, monkeypatch):
    mock_url = "https://cached-example.com"
    
    monkeypatch.setattr("app.api.v1.redirects.get_url", AsyncMock(return_value=mock_url))
    
    response = await client.get("/some-slug", follow_redirects=False)
    
    assert response.status_code == 307
    assert response.headers["location"] == mock_url

@pytest.mark.asyncio
async def test_create_link_collision_retry(client, monkeypatch):
    slugs = iter(["dup", "dup", "final"]) 
    monkeypatch.setattr("app.api.v1.links.generate_slug", lambda: next(slugs))

    await client.post("/api/v1/links", json={"url": "https://first.com"})

    resp = await client.post("/api/v1/links", json={"url": "https://second.com"})
    
    assert resp.status_code == 201
    assert resp.json()["slug"] == "final"