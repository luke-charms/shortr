import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_link_persists():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/links",
            json={"url": "https://example.com"}
        )
        assert response.status_code == 201
        data = response.json()
        print(f"\nDEBUG API RESPONSE: {data}") # See what's actually there
        assert data["url"] == "https://example.com/"
        assert "slug" in data

@pytest.mark.asyncio
async def test_create_link_invalid_url():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/links",
            json={"url": "not-a-url"}
        )

    assert response.status_code == 422