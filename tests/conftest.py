import pytest
import httpx
from app.main import app
from app.core.client import init_http_client, close_http_client


@pytest.fixture
async def client():
    """Async test client with active application lifespan."""
    await init_http_client()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    await close_http_client()
