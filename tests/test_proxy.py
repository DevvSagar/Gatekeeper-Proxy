import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """
    Test that the root metadata endpoint returns HTTP 200 and correct app name.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["service"] == "GateKeeper"


@pytest.mark.asyncio
async def test_health_check():
    """
    Test that the Kubernetes/Docker health check returns HTTP 200 OK.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_proxy_forwarding_success(monkeypatch):
    """
    Test that incoming requests to /proxy/{path} are forwarded upstream,
    and the upstream response is returned with the 'x-gateway-proxy' header.
    """
    # 1. Simulate an upstream backend server returning a 200 OK with JSON
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"mock_data": "product_123", "method": request.method},
            headers={"content-type": "application/json"},
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

    # 2. Tell GateKeeper to use our mock client instead of real internet
    async def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.proxy.client.get_http_client", mock_get_client)

    # 3. Send request to GateKeeper proxy
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/proxy/products/123")

        # 4. Verify proxy returned upstream status, body, and custom gateway header
        assert response.status_code == 200
        assert response.json()["mock_data"] == "product_123"
        assert response.headers["x-gateway-proxy"] == "GateKeeper"


@pytest.mark.asyncio
async def test_proxy_upstream_timeout(monkeypatch):
    """
    Test that when an upstream service times out, GateKeeper returns HTTP 504 Gateway Timeout.
    """
    def mock_timeout_handler(request: httpx.Request):
        raise httpx.ConnectTimeout("Upstream server unresponsive")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_timeout_handler))

    async def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.proxy.client.get_http_client", mock_get_client)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/proxy/slow-service")

        assert response.status_code == 504
        assert response.json()["detail"] == "Upstream connection timed out"
