import pytest
import respx
import httpx
from app.config import settings


@pytest.mark.asyncio
async def test_health_check(client: httpx.AsyncClient):
    """Verify system health endpoint returns 200 OK and valid metadata."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == settings.APP_NAME


@pytest.mark.asyncio
async def test_tracing_middleware_generates_id(client: httpx.AsyncClient):
    """Verify tracing middleware generates X-Request-ID and X-Response-Time headers."""
    response = await client.get("/health")
    assert "x-request-id" in response.headers
    assert "x-response-time" in response.headers
    assert response.headers["x-request-id"] is not None


@pytest.mark.asyncio
async def test_tracing_middleware_preserves_custom_id(client: httpx.AsyncClient):
    """Verify tracing middleware preserves client-provided X-Request-ID."""
    custom_id = "test-custom-trace-uuid-12345"
    response = await client.get("/health", headers={"x-request-id": custom_id})
    assert response.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
@respx.mock
async def test_proxy_get_forwarding(client: httpx.AsyncClient):
    """Verify proxy transparently forwards GET requests to the upstream target."""
    upstream_route = respx.get("https://httpbin.org/get").respond(
        status_code=200,
        json={"message": "hello from upstream", "origin": "127.0.0.1"}
    )

    response = await client.get("/proxy/get?category=books")

    assert upstream_route.called
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "hello from upstream"
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
@respx.mock
async def test_proxy_post_with_body(client: httpx.AsyncClient):
    """Verify proxy forwards POST requests with JSON payload to upstream."""
    upstream_route = respx.post("https://httpbin.org/post").respond(
        status_code=201,
        json={"created": True, "id": "item_999"}
    )

    payload = {"title": "Test Item", "price": 49.99}
    response = await client.post("/proxy/post", json=payload)

    assert upstream_route.called
    assert response.status_code == 201
    assert response.json()["created"] is True


@pytest.mark.asyncio
@respx.mock
async def test_proxy_upstream_error_handling(client: httpx.AsyncClient):
    """Verify that network connection errors upstream return 502 Bad Gateway."""
    respx.get("https://httpbin.org/broken").mock(
        side_effect=httpx.ConnectError("Failed to resolve host")
    )

    response = await client.get("/proxy/broken")
    assert response.status_code == 502
    assert "Bad Gateway" in response.json()["detail"]
