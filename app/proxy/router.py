import logging
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.config import settings
from app.core.client import get_http_client

logger = logging.getLogger("gatekeeper.proxy")

router = APIRouter()

# Hop-by-hop headers per RFC 7230 section 6.1 that must not be forwarded by a proxy
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def filter_request_headers(request: Request, client_ip: str, request_id: str) -> dict[str, str]:
    """
    Sanitize incoming headers: remove hop-by-hop headers,
    and attach standard forwarding headers (X-Forwarded-For, X-Request-ID).
    """
    filtered = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    # Append standard proxy forwarding headers
    existing_forwarded = filtered.get("x-forwarded-for")
    if existing_forwarded:
        filtered["x-forwarded-for"] = f"{existing_forwarded}, {client_ip}"
    else:
        filtered["x-forwarded-for"] = client_ip

    filtered["x-forwarded-proto"] = request.url.scheme
    filtered["x-request-id"] = request_id

    return filtered


def filter_response_headers(upstream_headers: httpx.Headers) -> dict[str, str]:
    """Sanitize upstream response headers before forwarding back to client."""
    return {
        key: value
        for key, value in upstream_headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }


@router.api_route(
    "/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    include_in_schema=True,
    summary="Reverse proxy endpoint forwarding to configured upstream",
)
async def proxy_endpoint(request: Request, path: str = ""):
    """
    Transparent asynchronous reverse proxy handler.
    Streams request body to upstream and streams response chunks back to the client.
    """
    client = get_http_client()
    client_ip = request.client.host if request.client else "127.0.0.1"
    request_id = getattr(request.state, "request_id", "unknown")

    # Build upstream target URL
    upstream_base = settings.UPSTREAM_URL.rstrip("/")
    clean_path = path.lstrip("/")
    target_url = f"{upstream_base}/{clean_path}" if clean_path else upstream_base

    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = filter_request_headers(request, client_ip, request_id)

    try:
        # Build upstream streaming request
        upstream_req = client.build_request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=request.stream(),
        )

        upstream_res = await client.send(upstream_req, stream=True)

    except httpx.ConnectTimeout:
        logger.error(f"[{request_id}] Gateway Timeout connecting to upstream: {target_url}")
        raise HTTPException(status_code=504, detail="Gateway Timeout: Upstream connection timed out")
    except httpx.ConnectError as err:
        logger.error(f"[{request_id}] Bad Gateway: Failed to connect to upstream ({err})")
        raise HTTPException(status_code=502, detail=f"Bad Gateway: Unable to reach upstream ({str(err)})")
    except Exception as exc:
        logger.error(f"[{request_id}] Proxy forwarding error: {exc}")
        raise HTTPException(status_code=500, detail="Internal Gateway Error")

    response_headers = filter_response_headers(upstream_res.headers)

    # Stream chunks directly back to the client to keep memory footprint minimal
    return StreamingResponse(
        upstream_res.aiter_raw(),
        status_code=upstream_res.status_code,
        headers=response_headers,
        background=upstream_res.aclose,
    )
