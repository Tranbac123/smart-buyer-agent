# packages/tools/tools/search_web.py
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError


logger = logging.getLogger("quantumx.tools.web_search")

SERPER_ENDPOINT = "https://google.serper.dev/search"
SERPER_API_KEY_ENV = "SERPER_API_KEY"
class WebSearchInput(BaseModel):
    """User-facing input for WebSearchTool."""

    query: str = Field(min_length=1)
    num_results: int = Field(default=5, ge=1, le=20)

    # "search" is standard web search; "news" and "shopping" are optional modes
    search_type: Literal["search", "news", "shopping"] = Field(default="search")
    # Geo and language hints; adjust to your primary market
    gl: str = Field(default="vn")  # country code
    hl: str = Field(default="vi")  # UI language

    use_cache: bool = True
    cache_ttl_sec: Optional[int] = Field(default=None, ge=60, le=3600)

    # Optional per-call overrides (fallback to runtime/global defaults)
    timeout_sec: Optional[int] = Field(default=None, gt=0)
    max_retries: Optional[int] = Field(default=None, ge=0, le=5)
    backoff_base_ms: Optional[int] = Field(default=None, ge=50, le=10000)

    tag: Optional[str] = Field(default=None)

class WebSearchItem(BaseModel):
    """Normalized search result item."""
    title: str
    url: str
    snippet: Optional[str] = None

    source: str = "serper"
    position: int = 0

    favicon_url: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)

class WebSearchResult(BaseModel):
    """Structured result with metadata."""

    query: str
    items: List[WebSearchItem]
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Cache backend (pluggable)
class WebSearchCacheBackend(Protocol):
    async def get(self, key: str) -> Optional[WebSearchResult]: ...
    async def set(self, key: str, value: WebSearchResult, ttl_sec: int) -> None: ...

class InMemoryWebSearchCache(WebSearchCacheBackend):
    """Process-local cache backend suitable for dev/test workloads."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[float, WebSearchResult]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[WebSearchResult]:
        now = time.time()
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expire_ts, result = item
            if expire_ts < now:
                self._store.pop(key, None)
                return None
            return result

    async def set(self, key: str, value: WebSearchResult, ttl_sec: int) -> None:
        expire_ts = time.time() + ttl_sec
        async with self._lock:
            self._store[key] = (expire_ts, value)

# Runtime overrides

@dataclass
class WebSearchRuntimeOverrides:
    timeout_sec: float
    max_retries: int
    backoff_base_ms: int
    cache_ttl_sec: Optional[int]

# WebSearchTool implementation

class WebSearchTool:
    """
    Web search tool backed by Serper.dev.

    Responsibilities
    ----------------
    * Accept a single search query with optional num_results, type, locale.
    * Call Serper.dev /search endpoint with an API key.
    * Apply timeout/retry/backoff and optional in-memory caching.
    * Read runtime overrides from RequestContext-like objects (ctx).
    * Return normalized list of {title, url, snippet, position, raw}.
    """
    name = "web_search"
    input_model = WebSearchInput
    output_model = WebSearchResult

    def __init__(
        self,
        *,
        client: Optional[httpx.AsyncClient] = None,
        cache: Optional[WebSearchCacheBackend] = None,
        default_timeout_sec: float = 6.0,
        default_max_retries: int = 1,
        default_backoff_base_ms: int = 200,
        default_cache_ttl_sec: int = 300,
        api_key: Optional[str] = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(default_timeout_sec),
        )
        self._owns_client = client is None
        self._cache = cache or InMemoryWebSearchCache()
        self._default_timeout_sec = float(max(0.2, default_timeout_sec))
        self._default_max_retries = int(max(0, default_max_retries))
        self._default_backoff_base_ms = int(max(50, default_backoff_base_ms))
        self._default_cache_ttl_sec = int(max(0, default_cache_ttl_sec))

        self._api_key = api_key or os.getenv(SERPER_API_KEY_ENV)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
    
    async def call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generic entrypoint for ControlPlane/ToolRegistry (dict in, dict out)."""
        data = dict(payload or {})
        ctx = data.pop("_ctx", None) or data.pop("ctx", None) or data.pop("request_ctx", None)

        # Allow passing input fields at top-level
        try:
            inp = WebSearchInput(**data)
        except ValidationError as e:
            logger.error("WebSearchTool input validation failed: %s", e)
            return {
                "query": data.get("query") or "",
                "items": [],
                "metadata": {
                    "error": "validation_error",
                    "detail": e.errors(),
                },
            }

        try:
            result = await self.run(inp, ctx=ctx)
        except Exception as e:
            logger.exception("WebSearchTool.run failed: %s", e)
            return {
                "query": inp.query,
                "items": [],
                "metadata": {
                    "error": "web_search_failure",
                    "detail": str(e),
                },
            }
        return result.model_dump(mode="json")

    async def run(self, inp: WebSearchInput, ctx: Any = None) -> WebSearchResult:
        """Typed entrypoint for Python callers (Agent nodes, engines, etc.)."""
        if not inp.query.strip():
            return WebSearchResult(query=inp.query, items=[], metadata={"note": "empty_query"})

        if not self._api_key:
            logger.error("WebSearchTool: SERPER_API_KEY is not configured")
            return WebSearchResult(
                query=inp.query,
                items=[],
                metadata={"error": "missing_api_key"},
            )

        overrides = self._runtime_overrides(inp, ctx)
        cache_key = self._build_cache_key(inp)

        if inp.use_cache and cache_key:
            cached = await self._cache.get(cache_key)
            if cached:
                items_copy = [item.model_copy(deep=True) for item in cached.items]
                meta = dict(cached.metadata)
                meta["from_cache"] = True
                return WebSearchResult(query=cached.query, items=items_copy, metadata=meta)

        started = time.perf_counter()
        data, error, retries = await self._search_with_retry(inp, overrides)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if error or not isinstance(data, dict):
            metadata = {
                "error": error or "invalid_response",
                "latency_ms": elapsed_ms,
                "retries": retries,
            }
            self._enrich_metadata_with_ctx(metadata, ctx)
            return WebSearchResult(query=inp.query, items=[], metadata=metadata)

        items = self._parse_results(inp, data)
        metadata = {
            "latency_ms": elapsed_ms,
            "retries": retries,
            "result_count": len(items),
            "search_type": inp.search_type,
            "gl": inp.gl,
            "hl": inp.hl,
        }
        self._enrich_metadata_with_ctx(metadata, ctx)

        result = WebSearchResult(query=inp.query, items=items, metadata=metadata)

        if inp.use_cache and cache_key:
            ttl = self._coerce_cache_ttl(inp.cache_ttl_sec or overrides.cache_ttl_sec)
            if ttl:
                await self._cache.set(cache_key, result, ttl_sec=ttl)

        return result

    # ------------------------------------------------------------------ #
    # HTTP + retry/backoff
    # ------------------------------------------------------------------ #

    async def _search_with_retry(
        self,
        inp: WebSearchInput,
        overrides: WebSearchRuntimeOverrides,
    ) -> tuple[Optional[Dict[str, Any]], Optional[str], int]:
        timeout = overrides.timeout_sec
        max_retries = overrides.max_retries
        backoff_base_ms = overrides.backoff_base_ms

        headers = {
            "X-API-KEY": self._api_key or "",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "q": inp.query,
            "num": inp.num_results,
            "gl": inp.gl,
            "hl": inp.hl,
        }

        # Serper uses the same endpoint for multiple "types" but with different parameters.
        if inp.search_type == "news":
            payload["type"] = "news"
        elif inp.search_type == "shopping":
            payload["type"] = "shopping"

        attempt = 0
        last_error: Optional[str] = None

        while True:
            try:
                response = await self._client.post(
                    SERPER_ENDPOINT,
                    headers=headers,
                    content=json.dumps(payload),
                    timeout=timeout,
                )
                if not response.is_success:
                    last_error = f"http_status_{response.status_code}"
                else:
                    try:
                        data = response.json()
                    except Exception as e:
                        last_error = f"parse_error:{exc}"
                    else:
                        return data, None, attempt
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = str(exc)
            except Exception as e:  # pragma: no cover - defensive guard
                last_error = f"{type(exc).__name__}: {exc}"

            attempt += 1
            if attempt > max_retries:
                break

            await asyncio.sleep(self._compute_backoff(backoff_base_ms, attempt - 1))

        return None, last_error or "unknown_error", attempt

    # ------------------------------------------------------------------ #
    # Parsing + metadata
    # ------------------------------------------------------------------ #

    def _parse_results(self, inp: WebSearchInput, data: Dict[str, Any]) -> List[WebSearchItem]:
        items: List[WebSearchItem] = []

        # Serper "search" responses usually keep main results inside "organic"
        # For "news" or "shopping", they may use different keys.
        if inp.search_type == "news":
            raw_items = data.get("news") or []
        elif inp.search_type == "shopping":
            raw_items = data.get("shopping") or []
        else:
            raw_items = data.get("organic") or data.get("results") or []

        if not isinstance(raw_items, list):
            return items

        for idx, raw in enumerate(raw_items):
            if not isinstance(raw, dict):
                continue
            title = raw.get("title") or ""
            link = raw.get("link") or raw.get("url") or ""
            if not title or not link:
                continue

            snippet = raw.get("snippet") or raw.get("description") or None
            favicon = raw.get("favicon") or None

            try:
                item = WebSearchItem(
                    title=title,
                    url=link,
                    snippet=snippet,
                    source="serper",
                    position=idx,
                    favicon_url=favicon,
                    raw=raw,
                )
            except ValidationError:
                # Be strict on URL format but do not break the whole list
                continue

            items.append(item)
            if len(items) >= inp.num_results:
                break

        return items

    # ------------------------------------------------------------------ #
    # Cache key / runtime overrides / context helpers
    # ------------------------------------------------------------------ #

    def _build_cache_key(self, inp: WebSearchInput) -> Optional[str]:
        try:
            payload = {
                "q": inp.query,
                "num": inp.num_results,
                "type": inp.search_type,
                "gl": inp.gl,
                "hl": inp.hl,
            }
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        except TypeError:
            return None
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"web_search:{digest}"

    def _runtime_overrides(self, inp: WebSearchInput, ctx: Any) -> WebSearchRuntimeOverrides:
        timeout_sec = (
            inp.timeout_sec if inp.timeout_sec is not None else self._default_timeout_sec
        )
        max_retries = (
            inp.max_retries if inp.max_retries is not None else self._default_max_retries
        )
        backoff = (
            inp.backoff_base_ms
            if inp.backoff_base_ms is not None
            else self._default_backoff_base_ms
        )
        cache_ttl = inp.cache_ttl_sec

        timeout_ms_ctx = self._ctx_number(ctx, "web_search_timeout_ms")
        if timeout_ms_ctx is not None:
            timeout_sec = max(0.2, float(timeout_ms_ctx) / 1000.0)

        retries_ctx = self._ctx_int(ctx, "web_search_max_retries")
        if retries_ctx is not None:
            max_retries = max(0, retries_ctx)

        backoff_ctx = self._ctx_int(ctx, "web_search_backoff_base_ms")
        if backoff_ctx is not None:
            backoff = max(50, backoff_ctx)

        cache_ttl_ctx = self._ctx_int(ctx, "web_search_cache_ttl_sec")
        if cache_ttl_ctx is not None:
            cache_ttl = cache_ttl_ctx

        return WebSearchRuntimeOverrides(
            timeout_sec=timeout_sec,
            max_retries=max(0, max_retries),
            backoff_base_ms=max(50, backoff),
            cache_ttl_sec=cache_ttl,
        )

    def _compute_backoff(self, base_ms: int, retry_idx: int) -> float:
        delay_ms = base_ms * (2 ** max(0, retry_idx))
        return min(3_000, delay_ms) / 1000.0

    def _coerce_cache_ttl(self, ttl: Optional[int]) -> Optional[int]:
        if ttl is None:
            ttl = self._default_cache_ttl_sec
        if ttl is None or ttl <= 0:
            return None
        return ttl

    def _enrich_metadata_with_ctx(self, meta: Dict[str, Any], ctx: Any) -> None:
        for key in ("request_id", "org_id", "flow_name"):
            value = self._ctx_lookup(ctx, key)
            if value:
                meta[key] = value

    # ------------------------------------------------------------------ #
    # Context helpers
    # ------------------------------------------------------------------ #

    def _ctx_lookup(self, ctx: Any, key: str) -> Optional[Any]:
        if ctx is None:
            return None
        if isinstance(ctx, dict):
            if key in ctx:
                return ctx[key]
            meta = ctx.get("metadata")
            if isinstance(meta, dict) and key in meta:
                return meta[key]
            return None
        meta = getattr(ctx, "metadata", None)
        if isinstance(meta, dict) and key in meta:
            return meta.get(key)
        return getattr(ctx, key, None) if hasattr(ctx, key) else None

    def _ctx_int(self, ctx: Any, key: str) -> Optional[int]:
        value = self._ctx_lookup(ctx, key)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _ctx_number(self, ctx: Any, key: str) -> Optional[float]:
        value = self._ctx_lookup(ctx, key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def build_web_search_tool(
    *,
    client: Optional[httpx.AsyncClient] = None,
    cache: Optional[WebSearchCacheBackend] = None,
    default_timeout_sec: float = 6.0,
    default_max_retries: int = 1,
    default_backoff_base_ms: int = 200,
    default_cache_ttl_sec: int = 300,
    api_key: Optional[str] = None,
) -> WebSearchTool:
    """
    Factory used by DI containers/providers to build a configured WebSearchTool.
    """

    return WebSearchTool(
        client=client,
        cache=cache,
        default_timeout_sec=default_timeout_sec,
        default_max_retries=default_max_retries,
        default_backoff_base_ms=default_backoff_base_ms,
        default_cache_ttl_sec=default_cache_ttl_sec,
        api_key=api_key,
    )