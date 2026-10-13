import httpx
from typing import Optional
from app.config import settings

# Global async HTTP client singleton with connection pooling
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Return the active HTTP client instance."""
    if _http_client is None or _http_client.is_closed:
        raise RuntimeError("HTTP client has not been initialized. Ensure application lifespan started.")
    return _http_client


async def init_http_client() -> httpx.AsyncClient:
    """
    Initialize persistent async HTTP client with connection pooling and keep-alive.
    This avoids re-negotiating TCP/TLS handshakes for every incoming proxy request.
    """
    global _http_client
    limits = httpx.Limits(
        max_keepalive_connections=50,
        max_connections=200,
        keepalive_expiry=30.0
    )
    timeout = httpx.Timeout(timeout=settings.PROXY_TIMEOUT_SECONDS, connect=5.0)

    _http_client = httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        follow_redirects=False  # Proxy should return redirects directly to client
    )
    return _http_client


async def close_http_client() -> None:
    """Gracefully close the global HTTP client and active connection pools."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
