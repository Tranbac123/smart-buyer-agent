# apps/api/src/main.py
from __future__ import annotations

import os
import sys
import logging
from contextlib import asynccontextmanager


import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# --- Optional imports (graceful if not present) ---
try:
    from api.http_gateway import mount_http_gateway
except Exception:  # pragma: no cover
    mount_http_gateway = None  # type: ignore

try:
    from api.telemetry.metrics import setup_metrics
except Exception:  # pragma: no cover
    setup_metrics = None  # type: ignore

try:
    from api.telemetry.tracing import setup_tracing
except Exception: # pragma: no cover
    setup_tracing = None

try:
    from api.errors.handlers import register_exception_handlers
except Exception: # pragma: no cover
    register_exception_handlers = None  # type: ignore

try:
    from config.settings import settings # your Pydantic Settings instance
except Exception: # pragma: no cover
    # Safe fallback if config module isn't wired yet
    class _fallback_settings:
        APP_NAME: str = "QuantumX API"
        APP_VERSION: str = "v1.0"
        CORS_ORIGINS: list[str] = ["*"]
        HTTPX_TIMEOUT: float = 10.0
        HTTPX_MAX_KEEPALIVE: int = 20
        HTTPX_LIMIT: tuple[int, int] = (100, 100) # (max_keepalive, max_connections)
        ENV: str = os.getenv("ENV", "dev")

# --- Logging bootstrap (simple, override via uvicorn config in prod) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("quantumx.api")

# --- Request ID middleware (simple & stateless) ---
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id")
    if not rid:
        import uuid
        rid = uuid.uuid4().hex
    # propagate via state & response header
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    return response

# --- Lifespan: init shared HTTP client, telemetry, etc. ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Shared httpx client (connection pooling across your site adapters/tools)
    max_keepalive, max_connections = getattr(settings, "HTTPX_LIMIT", (50, 100))
    app.state.http_client = httpx.AsyncClient(
        timeout=float(getattr(settings, "HTTPX_TIMEOUT", 15.0)),
        headers={"User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"},
        limits=httpx.Limits(
            max_keepalive_connections=int(max_keepalive),
            max_connections=int(max_connections),
        ),
        transport=httpx.AsyncHTTPTransport(retries=2),
    )
    # Telemetry hooks
    try:
        if setup_tracing:
            setup_tracing(app)
        if setup_metrics:
            setup_metrics(app)
    except Exception as e:  # pragma: no cover
        logger.warning("Telemetry setup failed: %s", e)
    
    logger.info("Startup complete | env : %s", getattr(settings, "ENV", "dev"))
    try:
        yield
    finally:
        try:
            await app.state.http_client.aclose()  # type: ignore[attr-defined]
        except Exception:
            pass
        logger.info("Shutdown complete")

    
def create_app() -> FastAPI:
    app = FastAPI(
        title=getattr(settings, "APP_NAME", "QuantumX API"),
        version=getattr(settings, "APP_VERSION", "v1.0"),
        docs_url=getattr(settings, "DOCS_URL", "/docs"),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    # Middlewares
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
    app.add_middleware("http")(request_id_middleware)

    # Error handlers (optional module)
    if register_exception_handlers:
        try:
            register_exception_handlers(app)
        except Exception as e: # pragma: no cover
            logger.warning("register_exception_handlers failed: %s", e)

    # Mount HTTP gateway (includes /v1 routes like /smart-buyer, /chat, /healthz)
    if mount_http_gateway:
        try:
            mount_http_gateway(app)
        except Exception as e: # pragma: no cover
            logger.error("mount_http_gateway failed: %s", e)
            # Provide a minimal fallback so the app still boots
            @app.get("/healthz", tags=["health"])
            async def healthz() -> dict:
                return {"status": "ok", "warning": "gateway_not_mounted"}
    else:
        # Minimal fallback when gateway is not ready
        @app.get("/healthz", tags=["health"])
        async def healthz() -> dict:
            return {"status": "ok", "note": "basic_health_only"}

    # root_ping
    @app.get("/", include_in_schema=False)
    async def _root_ping():
        return JSONResponse({"name": settings.APP_NAME, "version": settings.APP_VERSION})
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "dev") == "dev",
        forward_allow_ips="*",
        proxy_headers=True,
    )