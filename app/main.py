from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.links import router as links_router
from app.api.v1.redirects import router as redirect_router
from app.middleware.timing import TimingMiddleware
from app.core.redis import close_redis



@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: nothing to do — connections are lazy
    yield
    # shutdown: gracefully close the Redis connection pool
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(title="shortr", lifespan=lifespan)

    app.include_router(health_router)
    app.include_router(links_router)
    app.include_router(redirect_router)
    app.add_middleware(TimingMiddleware)

    return app


app = create_app()