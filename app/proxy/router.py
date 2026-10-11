import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.config import settings
from app.proxy import client as client_module

router = APIRouter(prefix="/proxy", tags=["Reverse Proxy"])

# Hop-by-hop headers that should not be forwarded
# (These belong to a single transport-level connection and shouldn't be forwarded by proxies)
EXCLUDED_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
}


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    summary="Reverse Proxy Ingress",
    description="Captures and forwards requests to the configured upstream backend service asynchronously.",
)
async def proxy_pass(request: Request, path: str) -> Response:
    """
    Reverse proxy endpoint.
    Receives incoming client traffic and asynchronously relays it to UPSTREAM_URL.
    """
    client = await client_module.get_http_client()

    # Construct the target upstream URL
    upstream_target = f"{settings.UPSTREAM_URL.rstrip('/')}/{path}"

    # Forward incoming headers, excluding connection/hop-by-hop headers
    forward_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in EXCLUDED_HEADERS
    }
    # Add a standard reverse-proxy header identifying the original client IP
    client_ip = request.client.host if request.client else "unknown"
    forward_headers["x-forwarded-for"] = client_ip

    # Read incoming request body asynchronously
    body = await request.body()

    try:
        # Asynchronously forward the request to the upstream target
        upstream_response = await client.request(
            method=request.method,
            url=upstream_target,
            params=request.query_params,
            headers=forward_headers,
            content=body,
        )

        # Filter out hop-by-hop response headers before returning to client
        response_headers = {
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower() not in EXCLUDED_HEADERS
        }

        # Add Gateway custom identifying header
        response_headers["x-gateway-proxy"] = settings.APP_NAME

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type"),
        )

    except httpx.ConnectTimeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream connection timed out",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to connect to upstream service at {settings.UPSTREAM_URL}",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Proxy upstream error: {exc!s}",
        ) from exc
