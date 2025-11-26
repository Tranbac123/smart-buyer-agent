# apps/api/src/dependencies/http_client_provider.py
from __future__ import annotations

from typing import Optional

from fastapi import Request
import httpx

from config.settings import settings


def _build_shared_httpx_client() -> httpx.AsyncClient:
    """
    Create a shared AsyncClient using app settings.
    This is only called if a client is missing or was closed.
    """
    # Connection limits (keepalive pool + total concurrent)
    keepalive, max_conn = settings.HTTPX_LIMITS  # computed_field -> (keepalive, max_connections)

    limits = httpx.Limits(
        max_keepalive_connections=int(keepalive),
        max_connections=int(max_conn),
    )

    # Default headers (identifiable UA)
    headers = {
        "User-Agent": settings.HTTPX.user_agent,
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    # Timeouts: connect/read/write/pool
    timeout = httpx.Timeout(settings.HTTPX.timeout)

    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        limits=limits,
        follow_redirects=True,
        http2=True,  # better multiplexing when server supports it
    )


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    Dependency provider for a shared httpx.AsyncClient.

    Expected lifecycle:
    - Preferred: created in app lifespan (main.py) and stored at `app.state.http_client`.
    - Fallback: if missing/closed, we lazily create a new shared client here.

    Always return a live AsyncClient instance.
    """
    client: Optional[httpx.AsyncClient] = getattr(request.app.state, "http_client", None)

    if client is None or getattr(client, "is_closed", False):
        # Lazily create and attach to app state so subsequent requests reuse it.
        client = _build_shared_httpx_client()
        request.app.state.http_client = client

    return client
