from __future__ import annotations

from fastapi import FastAPI
import logging
from typing import List, Dict, Any

# Settings are optional here; we fall back to sane defaults if the module isn't wired yet
try:
    from apps.api.src.config import settings
except ImportError:  # pragma: no cover
    class _FallbackSettings:
        APP_VERSION = "v1"
    settings = _FallbackSettings() # type: ignore

logger = logging.getLogger("quantumx.http_gateway")


def _api_prefix() -> str:
    v = getattr(settings, "APP_VERSION", "v1")
    v = v.lower().strip()
    return f"/{v}" if not v.startswith("/") else v

def _openapi_tags() -> List[Dict[str, Any]]:
    return [
        {"name": "health", "description": "Health and Readiness check"},
        {"name": "smart-buyer", "description": "Price compare + decision support"},
        {"name": "chat", "description": "General chat endpoints (optional)"},
    ]

def mount_http_gateway(app: FastAPI) -> None:
    """
    Mount all public HTTP routes under a single versioned prefix.
    This function is idempotent and safe to call during app startup.
    """
    prefix = _api_prefix()
    app.openapi_tags = _openapi_tags()  # type: ignore[attr-defined]

    # --- Import routers lazily (so app can boot even if a feature is not ready) ---
    health_router = None
    smart_buyer_router = None
    chat_router = None

    try:
        from api.routes import health as _health
        health_router = _health.router
    except ImportError as e:
        logger.warning("health router not available: %s", e)
    
    try:
        from api.routes import smart_buyer as _smart_buyer
        smart_buyer_router = _smart_buyer.router
    except Exception as e:  # pragma: no cover
        logger.warning("smart_buyer router not available: %s", e)

    # Optional chat module (if you add it later)
    try:
        from api.routes import chat as _chat  # noqa: F401
        chat_router = _chat.router  # type: ignore[attr-defined]
    except Exception:
        pass

    # --- Attach routers under versioned prefix ---
    if health_router is not None:
        app.include_router(health_router, prefix=prefix)
    else:
        @app.get(f"{prefix}/healthz", tags=["health"])
        async def _healthz_fallback():
            return {"status": "ok", "note": "health router missing"}

    if smart_buyer_router is not None:
        app.include_router(smart_buyer_router, prefix=prefix)

    if chat_router is not None:
        app.include_router(chat_router, prefix=prefix)

    # Minimal ping (outside docs) for quick sanity checks
    @app.get(f"{prefix}/ping", include_in_schema=False)
    async def _ping():
        return {"pong": True, "version": getattr(settings, "APP_VERSION", "v1")}
