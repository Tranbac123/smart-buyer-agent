# apps/api/src/api/routes/health.py
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from config.settings import settings

router = APIRouter(tags=["health"])


def _uptime_seconds(request: Request) -> float:
    start: Optional[float] = getattr(request.app.state, "start_time", None)
    if start is None:
        return 0.0
    return max(0.0, time.monotonic() - start)


def _fmt_seconds(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# FastAPI Path Operation Function Lifecycle:
# (Also called: endpoint function, route handler, path operation)
#
# 1. When file is imported:
#    - Decorator @router.get("/healthz") executes
#    - Function 'healthz' is registered to the router
#    - Function body is NOT executed yet
#
# 2. When Uvicorn starts:
#    - Server starts and listens for requests
#    - Function 'healthz' still NOT called
#
# 3. When HTTP GET /healthz request arrives:
#    - Router matches the route
#    - FastAPI invokes the 'healthz' function:
#      • async functions → run in the event loop
#      • sync functions → run in a threadpool
#    - Response is sent to client
#
# 👉 This is the ONLY time the healthz function actually executes.
# [Import file]
#      ↓
# [Decorator registers route]
#      ↓
# [include_router → app.routing_table.append(...)]
#      ↓
# [Uvicorn starts ASGI server]
#      ↓
# [Client sends GET /healthz]
#      ↓
# [Router matches /healthz]
#      ↓
# [FastAPI calls: await healthz(request)]
#      ↓
# [Return {"status": "ok"}]
#      ↓
# [Response to client]

@router.get("/healthz")
async def healthz(request: Request) -> Dict[str, Any]:
    """
    Liveness probe: returns 200 if the process is up.
    Avoids heavy checks; safe for frequent polling.
    """
    uptime = _uptime_seconds(request)
    return {
        "status": "ok",
        "app": getattr(settings, "APP_NAME", "QuantumX API"),
        "version": getattr(settings, "APP_VERSION", "v1"),
        "env": getattr(settings, "ENV", "dev"),
        "uptime_s": round(uptime, 3),
        "uptime_hms": _fmt_seconds(uptime),
    }


@router.get("/readyz")
async def readyz(request: Request) -> Dict[str, Any]:
    """
    Readiness probe: performs lightweight dependency checks.
    - http client (shared in app.state.http_client)
    - Redis (if enabled in settings)
    - Postgres (if enabled in settings)
    Any failing check marks overall status = "degraded".
    """
    checks: Dict[str, Any] = {}
    overall = "ok"

    # 1) http client (from lifespan)
    try:
        http_client = getattr(request.app.state, "http_client", None)
        if http_client is None:
            checks["http_client"] = {"status": "missing"}
            overall = "degraded"
        else:
            # We don't call remote services here; just ensure object exists & not closed
            is_closed = getattr(http_client, "is_closed", False)
            checks["http_client"] = {"status": "ok" if not is_closed else "closed"}
            if is_closed:
                overall = "degraded"
    except Exception as e:
        checks["http_client"] = {"status": "error", "error": f"{type(e).__name__}: {e}"}
        overall = "degraded"

    # 2) Redis (optional)
    try:
        if settings.REDIS.enabled and settings.REDIS.url:
            try:
                import redis.asyncio as aioredis  # type: ignore
                r = aioredis.from_url(settings.REDIS.url, decode_responses=True)
                pong = await r.ping()
                checks["redis"] = {"status": "ok" if pong else "no-pong"}
                if not pong:
                    overall = "degraded"
                await r.close()
            except ModuleNotFoundError:
                checks["redis"] = {"status": "skipped", "reason": "redis.asyncio not installed"}
            except Exception as e:
                checks["redis"] = {"status": "error", "error": f"{type(e).__name__}: {e}"}
                overall = "degraded"
        else:
            checks["redis"] = {"status": "disabled"}
    except Exception as e:
        checks["redis"] = {"status": "error", "error": f"{type(e).__name__}: {e}"}
        overall = "degraded"

    # 3) Postgres (optional)
    try:
        if settings.POSTGRES.enabled:
            dsn = getattr(settings, "DATABASE_URL", None)
            if not dsn:
                checks["postgres"] = {"status": "error", "error": "no DSN"}
                overall = "degraded"
            else:
                # Try async psycopg first; fall back to asyncpg; otherwise skip.
                connected = False
                err: Optional[str] = None

                try:
                    import psycopg  # type: ignore
                    from psycopg.rows import tuple_row  # noqa: F401
                    # psycopg (v3) async connection
                    async with await psycopg.AsyncConnection.connect(dsn) as conn:  # type: ignore[attr-defined]
                        async with conn.cursor() as cur:
                            await cur.execute("SELECT 1;")
                            _ = await cur.fetchone()
                            connected = True
                except ModuleNotFoundError:
                    try:
                        import asyncpg  # type: ignore
                        conn = await asyncpg.connect(dsn)
                        try:
                            _ = await conn.fetchval("SELECT 1;")
                            connected = True
                        finally:
                            await conn.close()
                    except ModuleNotFoundError:
                        err = "no psycopg(async) or asyncpg installed"
                    except Exception as e:
                        err = f"{type(e).__name__}: {e}"
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"

                if connected:
                    checks["postgres"] = {"status": "ok"}
                else:
                    checks["postgres"] = {"status": "error", "error": err or "unknown"}
                    overall = "degraded"
        else:
            checks["postgres"] = {"status": "disabled"}
    except Exception as e:
        checks["postgres"] = {"status": "error", "error": f"{type(e).__name__}: {e}"}
        overall = "degraded"

    uptime = _uptime_seconds(request)
    return {
        "status": overall,
        "checks": checks,
        "version": getattr(settings, "APP_VERSION", "v1"),
        "env": getattr(settings, "ENV", "dev"),
        "uptime_s": round(uptime, 3),
        "uptime_hms": _fmt_seconds(uptime),
    }


@router.get("/info")
async def info(request: Request) -> Dict[str, Any]:
    """
    Informational endpoint: build/environment details.
    Safe to expose in internal environments; review before exposing publicly.
    """
    uptime = _uptime_seconds(request)
    cors_any = getattr(settings, "ANY_CORS", False)

    return {
        "app": getattr(settings, "APP_NAME", "QuantumX API"),
        "version": getattr(settings, "APP_VERSION", "v1"),
        "env": getattr(settings, "ENV", "dev"),
        "debug": getattr(settings, "DEBUG", False),
        "features": getattr(settings, "FEATURES", None).model_dump() if getattr(settings, "FEATURES", None) else {},
        "limits": {
            "rate_limit_global": getattr(settings, "RATE_LIMIT_GLOBAL", None),
            "rate_limit_per_ip": getattr(settings, "RATE_LIMIT_PER_IP", None),
            "request_body_limit_mb": getattr(settings, "REQUEST_BODY_LIMIT_MB", None),
        },
        "httpx": {
            "timeout": getattr(settings.HTTPX, "timeout", None),
            "limits": getattr(settings, "HTTPX_LIMITS", None),
            "user_agent": getattr(settings.HTTPX, "user_agent", None),
        },
        "cors": {
            "any": bool(cors_any),
            "origins": getattr(settings, "CORS_ORIGINS", []),
        },
        "uptime_s": round(uptime, 3),
        "uptime_hms": _fmt_seconds(uptime),
    }
