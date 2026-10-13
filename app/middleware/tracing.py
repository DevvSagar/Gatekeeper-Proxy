import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("gatekeeper.trace")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Distributed Tracing Middleware:
    1. Extracts or generates a unique correlation ID (X-Request-ID).
    2. Measures total proxy request latency.
    3. Attaches X-Request-ID and X-Response-Time headers to the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # Extract or generate correlation ID
        request_id = request.headers.get("x-request-id")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for downstream handlers
        request.state.request_id = request_id

        # Proceed with request pipeline
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} failed after {duration_ms:.2f}ms: {exc}"
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Inject tracing headers into response
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time"] = f"{duration_ms:.2f}ms"

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)"
        )
        return response
