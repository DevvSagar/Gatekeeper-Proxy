from contextlib import asynccontextmanager

from fastapi import FastAPI, status

from app.core.config import settings
from app.proxy.client import close_http_client, get_http_client
from app.proxy.router import router as proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes shared async connection pools on startup,
    and cleanly closes connections on shutdown.
    """
    # Startup: Warm up async connection pool
    await get_http_client()
    yield
    # Shutdown: Cleanly close connection pool
    await close_http_client()


app = FastAPI(
    title=settings.APP_NAME,
    description="High-Throughput Asynchronous API Gateway & Reverse Proxy",
    version="0.1.0",
    lifespan=lifespan,
)

# Include the reverse proxy ingress router
app.include_router(proxy_router)


@app.get("/", tags=["System"])
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "online",
        "upstream_target": settings.UPSTREAM_URL,
        "docs": "/docs",
    }


@app.get("/health", tags=["System"], status_code=status.HTTP_200_OK)
async def health_check():
    """
    Kubernetes / Docker health probe endpoint.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
