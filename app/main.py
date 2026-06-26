import sys
sys.dont_write_bytecode = True

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.links import router as links_router
from app.api.v1.redirects import router as redirect_router
from app.middleware.timing import TimingMiddleware
from app.core.redis import close_redis

# Module-level imports so patch("app.main.flush_click_counts") works in tests
from app.workers.analytics_worker import (
    worker_loop,
    flush_click_counts,
    flush_click_events,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(worker_loop())

    yield

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    # Final drain — best-effort, must not prevent Redis from closing
    try:
        await flush_click_counts()
        await flush_click_events()
    except Exception:
        pass

    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(title="shortr", lifespan=lifespan)

    app.include_router(health_router)
    app.include_router(links_router)
    app.include_router(redirect_router)
    app.add_middleware(TimingMiddleware)

    return app


app = create_app()