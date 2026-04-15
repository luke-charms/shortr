from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.v1.links import router as links_router

def create_app() -> FastAPI:
    app = FastAPI(title="shortr")

    app.include_router(health_router)
    app.include_router(links_router)

    return app

app = create_app()