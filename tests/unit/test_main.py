import asyncio
import pytest
from unittest.mock import AsyncMock, patch


def test_create_app_returns_fastapi_instance():
    from fastapi import FastAPI
    from app.main import create_app
    assert isinstance(create_app(), FastAPI)


def test_create_app_registers_all_routers():
    from app.main import create_app
    app = create_app()
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/healthz" in routes
    assert "/api/v1/links" in routes
    assert "/{slug}" in routes


async def test_lifespan_starts_worker_and_shuts_down_cleanly():
    """
    Lifespan must start the worker task, cancel it on shutdown,
    call the final flush functions, and close Redis.

    flush_click_counts and flush_click_events are patched at app.main
    because they are imported at module level there — that's the name
    the lifespan closure actually calls.
    """
    async def hang():
        await asyncio.sleep(9999)

    # All three names are module-level in app.main after the fix
    with patch("app.main.worker_loop", side_effect=hang), \
         patch("app.main.flush_click_counts", new_callable=AsyncMock) as mock_counts, \
         patch("app.main.flush_click_events", new_callable=AsyncMock) as mock_events, \
         patch("app.main.close_redis", new_callable=AsyncMock) as mock_close:

        from app.main import create_app
        test_app = create_app()

        async with test_app.router.lifespan_context(test_app):
            pass  # enter = startup, exit = shutdown

        mock_counts.assert_called_once()
        mock_events.assert_called_once()
        mock_close.assert_called_once()