import inspect
import json
import logging
import os
import sys
import time
import uuid
import asyncio
from contextlib import nullcontext
from datetime import datetime
from typing import Dict, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import API_KEY, DOMAIN, env_or_config

try:
    from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

UPSTREAMS: Dict[str, str] = {
    "terminals": "http://open-terminal-api:8000",
    "memory": "http://memory-api:8001",
    "vector": "http://vector-memory-api:8002",
    "filesystem": "http://filesystem-api:8003",
    "summarizer": "http://summarizer-api:8004",
}

app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    description="FastAPI-basiertes API-Gateway, das Microservice-Anfragen an einzelne Backends weiterleitet.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

SERVICE_VERSION = "1.0.0"
SUPPORTED_API_VERSIONS = ["v1"]

LOG_LEVEL = env_or_config("API_GATEWAY_LOG_LEVEL", config_key="log_level", default="INFO").upper()
METRICS_ENABLED = env_or_config("API_GATEWAY_METRICS_ENABLED", config_key="metrics_enabled", default="true").lower() in ("1", "true", "yes")
RETRY_ATTEMPTS = int(env_or_config("API_GATEWAY_RETRY_ATTEMPTS", config_key="retry_attempts", default=2))
RETRY_BACKOFF_FACTOR = float(env_or_config("API_GATEWAY_RETRY_BACKOFF_FACTOR", config_key="retry_backoff_factor", default=0.25))
CIRCUIT_BREAKER_THRESHOLD = int(env_or_config("API_GATEWAY_CIRCUIT_BREAKER_THRESHOLD", config_key="circuit_breaker_threshold", default=5))
CIRCUIT_BREAKER_RESET = int(env_or_config("API_GATEWAY_CIRCUIT_BREAKER_RESET", config_key="circuit_breaker_reset", default=30))
CACHE_ENABLED = env_or_config("API_GATEWAY_CACHE_ENABLED", config_key="cache_enabled", default="false").lower() in ("1", "true", "yes")
CACHE_TTL = int(env_or_config("API_GATEWAY_CACHE_TTL", config_key="cache_ttl", default=60))

class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_fields"):
            payload.update(record.extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

logger = logging.getLogger("api_gateway")
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonLogFormatter())
logger.handlers = [handler]


def _current_request_id(request: Request) -> str:
    request_id = request.headers.get("x-request-id") or request.headers.get("traceparent")
    if request_id:
        return request_id
    return str(uuid.uuid4())


def _error_payload(status_code: int, title: str, detail: str, service: Optional[str] = None, request_id: Optional[str] = None) -> dict:
    payload = {
        "error": {
            "code": status_code,
            "title": title,
            "detail": detail,
            "request_id": request_id,
        }
    }
    if service:
        payload["error"]["service"] = service
    return payload

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range"],
)

app.mount(
    "/dashboard",
    StaticFiles(directory="dashboard", html=True),
    name="dashboard",
)

app.mount(
    "/.well-known/acme-challenge",
    StaticFiles(directory="/var/www/certbot"),
    name="acme",
)

PROTECTED_PREFIXES = ("/api/", "/openapi.json", "/docs", "/redoc")
EXEMPT_PATHS = ("/health", "/.well-known/acme-challenge")

DEFAULT_RATE_LIMIT = 60
DEFAULT_RATE_LIMIT_WINDOW = 60
RATE_LIMIT = int(env_or_config("API_GATEWAY_RATE_LIMIT", config_key="rate_limit", default=DEFAULT_RATE_LIMIT))
RATE_LIMIT_WINDOW = int(env_or_config("API_GATEWAY_RATE_LIMIT_WINDOW", config_key="rate_limit_window", default=DEFAULT_RATE_LIMIT_WINDOW))
RATE_LIMIT_PREFIXES = ("/api/",)
RATE_LIMIT_EXEMPT_PATHS = (
    "/health",
    "/.well-known/acme-challenge",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/dashboard",
)

CIRCUIT_BREAKER_STATE: Dict[str, dict] = {}
response_cache: Dict[str, Tuple[int, dict, bytes, float]] = {}

if PROMETHEUS_AVAILABLE and METRICS_ENABLED:
    REQUEST_COUNT = Counter(
        "api_gateway_requests_total",
        "Total number of API Gateway requests",
        ["service", "method", "status"],
    )
    REQUEST_DURATION = Histogram(
        "api_gateway_request_duration_seconds",
        "Latency of API Gateway requests",
        ["service", "method"],
    )
    UPSTREAM_ERRORS = Counter(
        "api_gateway_upstream_errors_total",
        "Total number of upstream errors",
        ["service", "reason"],
    )
    CIRCUIT_BREAKER_METRIC = Gauge(
        "api_gateway_circuit_breaker_open",
        "Circuit breaker open state per service",
        ["service"],
    )
else:
    REQUEST_COUNT = REQUEST_DURATION = UPSTREAM_ERRORS = CIRCUIT_BREAKER_METRIC = None

rate_limit_lock = asyncio.Lock()
rate_limit_state: Dict[str, Tuple[int, int]] = {}


def get_request_api_key(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()

    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key

    return request.query_params.get("api_key")


def _cache_key(request: Request, service: str, path: str) -> str:
    return f"{service}:{path}:{request.method}:{request.url.query}"


def requires_api_key(path: str) -> bool:
    if any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    return False


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    path = request.url.path

    if path in EXEMPT_PATHS or path.startswith("/.well-known/acme-challenge"):
        return await call_next(request)

    if requires_api_key(path):
        api_key = get_request_api_key(request)
        if api_key != API_KEY:
            logger.warning(
                "api_key_invalid",
                extra={
                    "extra_fields": {
                        "request_id": _current_request_id(request),
                        "path": path,
                        "provided_api_key": api_key[:8] + "..." if api_key else None,
                        "client": request.client.host if request.client else "unknown",
                    }
                },
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=_error_payload(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    title="Unauthorized",
                    detail="Invalid or missing API key",
                    request_id=_current_request_id(request),
                ),
            )

    if (
        request.url.scheme == "http"
        and request.url.port in (80, None)
        and not request.url.path.startswith("/.well-known/acme-challenge")
        and (request.url.hostname not in ("localhost", "127.0.0.1"))
    ):
        hostname = request.url.hostname or DOMAIN
        redirect_url = request.url.replace(scheme="https", netloc=hostname)
        return RedirectResponse(url=str(redirect_url), status_code=308)

    return await call_next(request)


def _get_client_identifier(request: Request) -> str:
    api_key = get_request_api_key(request)
    if api_key:
        return f"api_key:{api_key}"

    client_host = None
    if request.client:
        client_host = request.client.host
    elif request.headers.get("x-forwarded-for"):
        client_host = request.headers.get("x-forwarded-for").split(",")[0].strip()

    return f"ip:{client_host or 'unknown'}"


def _is_rate_limited_path(path: str) -> bool:
    if any(path.startswith(exempt) for exempt in RATE_LIMIT_EXEMPT_PATHS):
        return False
    return any(path.startswith(prefix) for prefix in RATE_LIMIT_PREFIXES)


def _circuit_breaker(service: str) -> dict:
    state = CIRCUIT_BREAKER_STATE.setdefault(
        service,
        {
            "failures": 0,
            "opened_at": None,
            "state": "closed",
        },
    )
    if state["state"] == "open":
        if state["opened_at"] and (time.time() - state["opened_at"] > CIRCUIT_BREAKER_RESET):
            state["state"] = "half_open"
            state["failures"] = 0
            state["opened_at"] = None
    return state


def _record_circuit_failure(service: str):
    state = _circuit_breaker(service)
    state["failures"] += 1
    if state["failures"] >= CIRCUIT_BREAKER_THRESHOLD:
        state["state"] = "open"
        state["opened_at"] = time.time()
        if CIRCUIT_BREAKER_METRIC:
            CIRCUIT_BREAKER_METRIC.labels(service=service).set(1)


def _record_circuit_success(service: str):
    state = _circuit_breaker(service)
    if state["state"] in ("half_open", "open"):
        state["state"] = "closed"
        state["failures"] = 0
        state["opened_at"] = None
        if CIRCUIT_BREAKER_METRIC:
            CIRCUIT_BREAKER_METRIC.labels(service=service).set(0)


async def _check_rate_limit(client_id: str) -> Tuple[bool, int, int, int]:
    now = int(time.time())
    window_start = now - (now % RATE_LIMIT_WINDOW)
    async with rate_limit_lock:
        count, start = rate_limit_state.get(client_id, (0, window_start))
        if start != window_start:
            count = 0
            start = window_start

        count += 1
        rate_limit_state[client_id] = (count, start)

    remaining = max(0, RATE_LIMIT - count)
    reset = start + RATE_LIMIT_WINDOW
    return count <= RATE_LIMIT, remaining, RATE_LIMIT, reset


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = _current_request_id(request)
    request.state.request_id = request_id
    request.state.start_time = time.time()

    logger.info(
        "incoming_request",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "path": request.url.path,
                "query": str(request.query_params),
                "method": request.method,
                "client": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            }
        },
    )

    response = await call_next(request)
    latency = time.time() - request.state.start_time
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_completed",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": int(latency * 1000),
                "service": request.url.path.split("/")[2] if len(request.url.path.split("/")) > 2 else "unknown",
            }
        },
    )

    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if _is_rate_limited_path(request.url.path):
        client_id = _get_client_identifier(request)
        allowed, remaining, limit, reset = await _check_rate_limit(client_id)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=_error_payload(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    title="Too many requests",
                    detail="Rate limit exceeded",
                    request_id=getattr(request.state, "request_id", None),
                ),
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        return response

    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else _error_payload(
        status_code=exc.status_code,
        title="HTTP Exception",
        detail=str(exc.detail),
        request_id=getattr(request.state, "request_id", None),
    )
    return JSONResponse(status_code=exc.status_code, content=detail)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "unhandled_exception",
        exc_info=exc,
        extra={
            "extra_fields": {
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
            }
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_payload(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal server error",
            detail="An unexpected error occurred in the API Gateway.",
            request_id=getattr(request.state, "request_id", None),
        ),
    )

http_client = httpx.AsyncClient(
    timeout=60.0,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    headers={"User-Agent": "api-gateway/1.0"},
)


def build_upstream_url(service: str, path: str) -> str:
    upstream = UPSTREAMS[service]
    if path:
        return f"{upstream}/{path}"
    return f"{upstream}/"


def filter_request_headers(request: Request) -> dict:
    headers = {}
    for name, value in request.headers.items():
        lower_name = name.lower()
        if lower_name in HOP_BY_HOP_HEADERS or lower_name == "host":
            continue
        headers[name] = value

    client_host = request.client.host if request.client else None
    if client_host:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            headers["X-Forwarded-For"] = f"{forwarded_for}, {client_host}"
        else:
            headers["X-Forwarded-For"] = client_host
        headers["X-Real-IP"] = client_host

    headers["X-Forwarded-Proto"] = request.url.scheme
    headers["X-API-Gateway"] = "true"
    return headers


def filter_response_headers(response: httpx.Response) -> dict:
    headers = {}
    for name, value in response.headers.items():
        if name.lower() in HOP_BY_HOP_HEADERS:
            continue
        headers[name] = value
    return headers


def list_gateway_functions() -> dict:
    routes = []
    route_names = set()

    from fastapi.routing import APIRoute

    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(
                {
                    "path": route.path,
                    "methods": sorted(route.methods),
                    "name": route.name,
                    "endpoint": route.endpoint.__name__,
                    "summary": route.summary or "",
                    "description": route.description or "",
                }
            )
            route_names.add(route.endpoint.__name__)

    helpers = []
    for name, func in inspect.getmembers(sys.modules[__name__], inspect.isfunction):
        if func.__module__ != __name__:
            continue
        if name in route_names:
            continue
        line = None
        try:
            _, line = inspect.getsourcelines(func)
        except (OSError, TypeError):
            line = None
        helpers.append(
            {
                "name": name,
                "doc": inspect.getdoc(func) or "",
                "line": line,
            }
        )

    helpers.sort(key=lambda item: item["name"])

    return {
        "routes": routes,
        "helpers": helpers,
    }


async def proxy_request(request: Request, service: str, path: str) -> Response:
    url = build_upstream_url(service, path)
    content = await request.body()
    headers = filter_request_headers(request)
    request_id = getattr(request.state, "request_id", _current_request_id(request))

    circuit_state = _circuit_breaker(service)
    if circuit_state["state"] == "open":
        logger.warning(
            "circuit_breaker_open",
            extra={
                "extra_fields": {
                    "service": service,
                    "request_id": request_id,
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_error_payload(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                title="Service temporarily unavailable",
                detail=f"Circuit breaker is open for upstream service '{service}'",
                service=service,
                request_id=request_id,
            ),
        )

    cache_key = _cache_key(request, service, path)
    if CACHE_ENABLED and request.method == "GET":
        cached = response_cache.get(cache_key)
        if cached and cached[3] > time.time():
            _, cached_headers, cached_body, _ = cached
            logger.info(
                "cache_hit",
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "service": service,
                        "path": path,
                    }
                },
            )
            return Response(
                content=cached_body,
                status_code=200,
                headers=cached_headers,
                media_type=cached_headers.get("content-type"),
            )

    last_exception = None
    for attempt in range(1, RETRY_ATTEMPTS + 2):
        try:
            with REQUEST_DURATION.labels(service=service, method=request.method).time() if REQUEST_DURATION else nullcontext():
                response = await http_client.request(
                    request.method,
                    url,
                    params=request.query_params,
                    content=content if content else None,
                    headers=headers,
                )

            if response.status_code >= 500:
                raise httpx.HTTPStatusError("Upstream server error", request=response.request, response=response)

            response_headers = filter_response_headers(response)
            if CACHE_ENABLED and request.method == "GET" and response.status_code == 200:
                response_cache[cache_key] = (
                    response.status_code,
                    response_headers,
                    response.content,
                    time.time() + CACHE_TTL,
                )

            _record_circuit_success(service)
            if REQUEST_COUNT:
                REQUEST_COUNT.labels(service=service, method=request.method, status=str(response.status_code)).inc()

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type"),
            )

        except Exception as exc:
            last_exception = exc
            _record_circuit_failure(service)
            if REQUEST_COUNT:
                REQUEST_COUNT.labels(service=service, method=request.method, status="error").inc()
            if UPSTREAM_ERRORS:
                UPSTREAM_ERRORS.labels(service=service, reason=type(exc).__name__).inc()

            logger.error(
                "upstream_request_failed",
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "service": service,
                        "attempt": attempt,
                        "error": str(exc),
                    }
                },
            )

            if attempt <= RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_FACTOR * attempt)
                continue
            break

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=_error_payload(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Bad gateway",
            detail=f"Failed to proxy request to upstream service '{service}': {last_exception}",
            service=service,
            request_id=request_id,
        ),
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await http_client.aclose()


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/")


@app.get("/health", include_in_schema=False)
async def health() -> str:
    return "OK"


@app.get("/api-info", include_in_schema=False)
async def api_info() -> dict:
    return {
        "gateway": "API Gateway v1.0",
        "version": SERVICE_VERSION,
        "supported_api_versions": SUPPORTED_API_VERSIONS,
        "services": ["terminal", "memory", "vector-memory", "filesystem", "summarizer"],
    }


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not PROMETHEUS_AVAILABLE or not METRICS_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrics endpoint is not enabled")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/functions", include_in_schema=False)
async def api_functions() -> dict:
    return list_gateway_functions()


@app.api_route("/api/terminals", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], include_in_schema=False)
async def terminal_redirect() -> Response:
    return RedirectResponse(url="/api/terminals/", status_code=308)


@app.api_route(
    "/api/terminals/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_terminals(path: str, request: Request) -> Response:
    return await proxy_request(request, "terminals", path)


@app.api_route(
    "/api/memory/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_memory(path: str, request: Request) -> Response:
    return await proxy_request(request, "memory", path)


@app.api_route(
    "/api/vector/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_vector(path: str, request: Request) -> Response:
    return await proxy_request(request, "vector", path)


@app.api_route(
    "/api/filesystem/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_filesystem(path: str, request: Request) -> Response:
    return await proxy_request(request, "filesystem", path)


@app.api_route(
    "/api/summarizer/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_summarizer(path: str, request: Request) -> Response:
    return await proxy_request(request, "summarizer", path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 80))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
