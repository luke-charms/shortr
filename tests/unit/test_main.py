import asyncio
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient


def test_create_app_returns_fastapi_instance():
    from fastapi import FastAPI
    from app.main import create_app
    assert isinstance(create_app(), FastAPI)


async def test_create_app_registers_health_route():
    """Verify /healthz is reachable — confirms the health router is registered."""
    from app.main import create_app
    test_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/healthz")
    assert response.status_code == 200


async def test_create_app_registers_links_route():
    """Verify POST /api/v1/links exists — confirms the links router is registered."""
    from app.main import create_app
    test_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # Sending no body returns 422 (validation error), not 404.
        # 422 proves the route exists; 404 would mean it's not registered.
        response = await client.post("/api/v1/links", json={})
    assert response.status_code != 404


async def test_create_app_registers_redirect_route():
    """Verify GET /{slug} exists — confirms the redirect router is registered."""
    from app.main import create_app
    test_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # An unknown slug returns 404 from our handler, not a routing 404.
        # The distinction: FastAPI returns {"detail": "Link not found"},
        # not {"detail": "Not Found"} (the generic routing miss message).
        response = await client.get("/some-slug", follow_redirects=False)
    assert response.json().get("detail") == "Link not found"


async def test_lifespan_starts_worker_and_shuts_down_cleanly():
    async def hang():
        await asyncio.sleep(9999)

    with patch("app.main.worker_loop", side_effect=hang), \
         patch("app.main.flush_click_counts", new_callable=AsyncMock) as mock_counts, \
         patch("app.main.flush_click_events", new_callable=AsyncMock) as mock_events, \
         patch("app.main.close_redis", new_callable=AsyncMock) as mock_close:

        from app.main import create_app
        test_app = create_app()

        async with test_app.router.lifespan_context(test_app):
            pass

        mock_counts.assert_called_once()
        mock_events.assert_called_once()
        mock_close.assert_called_once()