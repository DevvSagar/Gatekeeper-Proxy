import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.config import settings
from app.core.client import init_http_client, close_http_client
from app.middleware.tracing import RequestTracingMiddleware
from app.proxy.router import router as proxy_router

# Configure structured application logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gatekeeper")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycles."""
    logger.info("Initializing GateKeeper-Proxy services...")
    await init_http_client()
    logger.info(f"GateKeeper-Proxy running. Forwarding target: {settings.UPSTREAM_URL}")
    yield
    logger.info("Shutting down GateKeeper-Proxy services...")
    await close_http_client()
    logger.info("GateKeeper-Proxy cleanup complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="High-performance asynchronous API Gateway and Reverse Proxy",
    lifespan=lifespan,
)

# Attach distributed tracing & latency tracking middleware
app.add_middleware(RequestTracingMiddleware)

# Include core reverse-proxy router
app.include_router(proxy_router)


@app.get("/health", tags=["System"])
async def health_check():
    """System health check and upstream connectivity endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.APP_NAME,
            "environment": settings.ENV,
            "upstream_target": settings.UPSTREAM_URL,
        }
    )


@app.get("/", tags=["System"])
async def root():
    """Gateway welcome and entrypoint."""
    return {
        "message": "Welcome to GateKeeper-Proxy",
        "docs_url": "/docs",
        "health_check": "/health",
    }
