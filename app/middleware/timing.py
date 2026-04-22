import time
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()

        response = await call_next(request)

        duration = time.time() - start

        logger.info(f"{request.method} {request.url} took {duration:.4f}s")

        return response