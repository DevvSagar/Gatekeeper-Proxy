# GateKeeper-Proxy 🛡️

A high-performance, asynchronous API Gateway and Reverse Proxy built in Python using FastAPI, HTTPX, and Redis.

## Features
- **Asynchronous Reverse Proxy:** Full HTTP streaming with persistent connection pooling to upstream microservices.
- **Distributed Request Tracing:** Unique `X-Request-ID` correlation tracking and `X-Response-Time` latency reporting on every hop.
- **RFC 7230 Compliant:** Strips hop-by-hop headers while appending industry standard proxy headers (`X-Forwarded-For`, `X-Forwarded-Proto`).
- **Sliding-Window Rate Limiting:** *(Day 2)* Redis-backed traffic throttling using sorted sets.
- **Idempotency Guard:** *(Day 2)* Redis distributed locks ensuring exactly-once processing for mutations.
- **Dead Letter Queue (DLQ):** *(Day 3)* Resilient retry engine for failed async deliveries.

---

## Architecture Flow

```
Incoming Client Request
         │
         ▼
[GateKeeper-Proxy Gateway]
         │
         ├── 1. RequestTracingMiddleware (X-Request-ID, latency timers)
         ├── 2. Persistent HTTPX Connection Pool (Keep-Alive, zero handshake overhead)
         └── 3. Streaming Reverse Proxy Router
         │
         ▼
[Upstream Microservice / API]
```

---

## Quickstart (Powered by `uv`)

### 1. Setup Environment
```bash
# Create isolated virtual environment
uv venv .venv

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Run the Gateway Locally
```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Run Automated Tests
```bash
uv run pytest -v
```
