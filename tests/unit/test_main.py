"""
Unit tests for app/main.py
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_lifespan_calls_close_redis_on_shutdown():
    """
    The lifespan handler must call close_redis() on shutdown.

    We patch close_redis BEFORE calling create_app() so the lifespan
    closure captures the mock, then drive the lifespan context directly.
    """
    with patch("app.main.close_redis", new_callable=AsyncMock) as mock_close:
        # App must be created inside the patch so lifespan captures the mock
        test_app = create_app()

        # Drive lifespan manually: enter = startup, exit = shutdown
        async with test_app.router.lifespan_context(test_app):
            pass  # startup done, now trigger shutdown by exiting

        mock_close.assert_called_once()


def test_create_app_returns_fastapi_instance():
    from fastapi import FastAPI
    assert isinstance(create_app(), FastAPI)


def test_create_app_registers_all_routers():
    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/healthz" in routes
    assert "/api/v1/links" in routes
    assert "/{slug}" in routes