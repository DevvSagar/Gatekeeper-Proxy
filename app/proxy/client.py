
import httpx

# Global async HTTP client pool
# Reusing the client maintains open TCP connections (HTTP Keep-Alive),
# avoiding expensive TLS handshakes on every single forwarded request.
_async_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """
    Returns the shared singleton httpx.AsyncClient instance.
    """
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=200),
        )
    return _async_client


async def close_http_client() -> None:
    """
    Gracefully closes open connection pools during application shutdown.
    """
    global _async_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None
