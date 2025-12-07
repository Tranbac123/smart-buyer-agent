# packages/tools/tools/scraper_tool.py
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Protocol

import httpx
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator

logger = logging.getLogger("quantumx.tools.scraper")


# =============================================================================
# Pydantic request/response models
# =============================================================================


class ScraperRequest(BaseModel):
    url: HttpUrl
    method: Literal["GET", "POST"] = "GET"

    params: Dict[str, Any] = Field(default_factory=dict)
    data: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    parse_as: Literal["auto", "json", "text"] = "auto"

    use_cache: bool = True
    cache_ttl_sec: Optional[int] = Field(default=None, ge=0, le=3600)

    timeout_sec: Optional[float] = Field(default=None, gt=0)
    max_retries: Optional[int] = Field(default=None, ge=0, le=5)
    backoff_base_ms: Optional[int] = Field(default=None, ge=50, le=10_000)

    tag: Optional[str] = None

    @field_validator("method", mode="before")
    @classmethod
    def _normalize_method(cls, value: str) -> str:
        return str(value or "GET").upper()


class ScraperSingleResult(BaseModel):
    url: HttpUrl
    ok: bool
    status_code: Optional[int] = None

    text: Optional[str] = None
    json: Optional[Any] = None
    error: Optional[str] = None

    from_cache: bool = False
    elapsed_ms: Optional[int] = None
    retries: int = 0
    final_url: Optional[str] = None
    tag: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScraperBatchInput(BaseModel):
    requests: List[ScraperRequest]


class ScraperBatchResult(BaseModel):
    results: List[ScraperSingleResult]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Cache backend (pluggable)
# =============================================================================


class ScraperCacheBackend(Protocol):
    async def get(self, key: str) -> Optional[ScraperSingleResult]:
        ...

    async def set(self, key: str, value: ScraperSingleResult, ttl_sec: int) -> None:
        ...


class InMemoryScraperCache(ScraperCacheBackend):
    """Process-local cache backend suitable for dev/test workloads."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[float, ScraperSingleResult]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[ScraperSingleResult]:
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

    async def set(self, key: str, value: ScraperSingleResult, ttl_sec: int) -> None:
        expire_ts = time.time() + ttl_sec
        async with self._lock:
            self._store[key] = (expire_ts, value)


# =============================================================================
# ScraperTool implementation
# =============================================================================


@dataclass(frozen=True)
class RuntimeOverrides:
    timeout_sec: float
    max_retries: int
    backoff_base_ms: int
    cache_ttl_sec: Optional[int]


class ScraperTool:
    """
    Generic async HTTP fetcher for the agent stack.

    Responsibilities
    ----------------
    * Accept a batch of HTTP requests (URL, params, headers, parse mode, etc.).
    * Execute them concurrently using an httpx.AsyncClient with timeout/retry/backoff.
    * Apply optional context overrides (timeout/retry/cache TTL) sourced from RequestContext.metadata.
    * Cache successful responses by (method, url, params, data).
    * Return normalized per-request results plus aggregated metadata.
    """

    name = "scraper_fetch"
    input_model = ScraperBatchInput
    output_model = ScraperBatchResult

    _SINGLE_REQUEST_FIELDS = {
        "url",
        "method",
        "params",
        "data",
        "headers",
        "parse_as",
        "use_cache",
        "cache_ttl_sec",
        "timeout_sec",
        "max_retries",
        "backoff_base_ms",
        "tag",
    }

    def __init__(
        self,
        *,
        client: Optional[httpx.AsyncClient] = None,
        cache: Optional[ScraperCacheBackend] = None,
        default_timeout_sec: float = 6.0,
        default_max_retries: int = 1,
        default_backoff_base_ms: int = 200,
        default_cache_ttl_sec: int = 300,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(default_timeout_sec),
            follow_redirects=True,
        )
        self._owns_client = client is None
        self._cache = cache or InMemoryScraperCache()
        self._default_timeout_sec = float(max(0.2, default_timeout_sec))
        self._default_max_retries = int(max(0, default_max_retries))
        self._default_backoff_base_ms = int(max(50, default_backoff_base_ms))
        self._default_cache_ttl_sec = int(max(0, default_cache_ttl_sec))

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload or {})
        ctx = data.pop("_ctx", None) or data.pop("ctx", None) or data.pop("request_ctx", None)

        if "requests" not in data:
            single = self._extract_single_request(data)
            if single:
                for key in self._SINGLE_REQUEST_FIELDS:
                    data.pop(key, None)
                data["requests"] = [single]

        try:
            batch = ScraperBatchInput(**data)
        except ValidationError as exc:
            logger.warning("ScraperTool input validation failed: %s", exc)
            return {
                "results": [],
                "metadata": {
                    "error": "validation_error",
                    "detail": exc.errors(),
                },
            }

        try:
            result = await self.run(batch, ctx=ctx)
        except Exception as e:  # pragma: no cover - defensive guard
            logger.exception("ScraperTool.run failed: %s", exc)
            return {
                "results": [],
                "metadata": {
                    "error": "scraper_failure",
                    "detail": str(exc),
                },
            }

        return result.model_dump(mode="json")

    async def run(self, inp: ScraperBatchInput, ctx: Any = None) -> ScraperBatchResult:
        if not inp.requests:
            return ScraperBatchResult(results=[], metadata={"batch_size": 0, "note": "no_requests"})

        overrides = self._runtime_overrides(ctx)
        started = time.perf_counter()
        gathered = await asyncio.gather(
            *(self._handle_one(req, overrides) for req in inp.requests),
            return_exceptions=True,
        )
        normalized = [self._normalize_result(req, res) for req, res in zip(inp.requests, gathered)]
        metadata = self._build_batch_metadata(normalized, ctx, started)
        return ScraperBatchResult(results=normalized, metadata=metadata)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _extract_single_request(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "url" not in data:
            return None
        return {k: data.get(k) for k in self._SINGLE_REQUEST_FIELDS if k in data}

    def _normalize_result(
        self,
        req: ScraperRequest,
        result: ScraperSingleResult | BaseException,
    ) -> ScraperSingleResult:
        if isinstance(result, ScraperSingleResult):
            return result
        error = str(result)
        return ScraperSingleResult(
            url=req.url,
            ok=False,
            status_code=None,
            error=error,
            from_cache=False,
            retries=0,
            final_url=str(req.url),
            tag=req.tag,
            metadata={"exception": True},
        )

    async def _handle_one(
        self,
        req: ScraperRequest,
        overrides: RuntimeOverrides,
    ) -> ScraperSingleResult:
        cache_key = self._build_cache_key(req)
        if req.use_cache and cache_key:
            cached = await self._cache.get(cache_key)
            if cached:
                copy = cached.model_copy(deep=True)
                copy.from_cache = True
                copy.metadata = {**(cached.metadata or {}), "cache_hit": True}
                return copy

        result = await self._fetch_with_retry(req, overrides)

        if req.use_cache and cache_key and result.ok:
            ttl = req.cache_ttl_sec if req.cache_ttl_sec is not None else overrides.cache_ttl_sec
            ttl = self._coerce_cache_ttl(ttl)
            if ttl:
                await self._cache.set(cache_key, result, ttl_sec=ttl)

        return result

    def _build_cache_key(self, req: ScraperRequest) -> Optional[str]:
        try:
            payload = {
                "method": req.method,
                "url": str(req.url),
                "params": req.params,
                "data": req.data,
            }
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        except TypeError:
            return None
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"scraper:{digest}"

    async def _fetch_with_retry(
        self,
        req: ScraperRequest,
        overrides: RuntimeOverrides,
    ) -> ScraperSingleResult:
        timeout = req.timeout_sec if req.timeout_sec is not None else overrides.timeout_sec
        max_retries = req.max_retries if req.max_retries is not None else overrides.max_retries
        backoff_base_ms = (
            req.backoff_base_ms if req.backoff_base_ms is not None else overrides.backoff_base_ms
        )

        attempt = 0
        last_error: Optional[str] = None
        started = time.perf_counter()

        while True:
            try:
                response = await self._client.request(
                    req.method,
                    str(req.url),
                    params=req.params or None,
                    data=req.data or None,
                    headers=req.headers or None,
                    timeout=timeout,
                )
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                return await self._build_result_from_response(
                    req=req,
                    resp=response,
                    elapsed_ms=elapsed_ms,
                    retries=attempt,
                )
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = str(exc)
            except Exception as e:  # pragma: no cover - defensive guard
                last_error = f"{type(exc).__name__}: {exc}"
            attempt += 1
            if attempt > max_retries:
                break
            await asyncio.sleep(self._compute_backoff(backoff_base_ms, attempt - 1))

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return ScraperSingleResult(
            url=req.url,
            ok=False,
            status_code=None,
            error=last_error or "unknown_error",
            from_cache=False,
            elapsed_ms=elapsed_ms,
            retries=attempt,
            final_url=str(req.url),
            tag=req.tag,
            metadata={"network_error": True},
        )

    async def _build_result_from_response(
        self,
        req: ScraperRequest,
        resp: httpx.Response,
        elapsed_ms: int,
        retries: int,
    ) -> ScraperSingleResult:
        parse_mode = req.parse_as
        if parse_mode == "auto":
            ctype = resp.headers.get("content-type", "")
            parse_mode = "json" if "application/json" in ctype else "text"

        text_body: Optional[str] = None
        json_body: Optional[Any] = None
        error: Optional[str] = None

        try:
            if parse_mode == "json":
                json_body = resp.json()
            else:
                text_body = resp.text
        except Exception as e:
            error = f"parse_error: {exc}"

        ok = resp.is_success and error is None

        return ScraperSingleResult(
            url=req.url,
            ok=ok,
            status_code=resp.status_code,
            text=text_body if parse_mode == "text" else None,
            json=json_body if parse_mode == "json" else None,
            error=error,
            from_cache=False,
            elapsed_ms=elapsed_ms,
            retries=retries,
            final_url=str(resp.url),
            tag=req.tag,
            metadata={
                "parse_mode": parse_mode,
                "headers": dict(resp.headers),
            },
        )

    def _compute_backoff(self, base_ms: int, retry_idx: int) -> float:
        delay_ms = base_ms * (2 ** max(0, retry_idx))
        # Cap backoff to a sane max (3s) to avoid runaway waits.
        return min(3_000, delay_ms) / 1000.0

    def _coerce_cache_ttl(self, ttl: Optional[int]) -> Optional[int]:
        if ttl is None:
            ttl = self._default_cache_ttl_sec
        if ttl is None or ttl <= 0:
            return None
        return ttl

    def _runtime_overrides(self, ctx: Any) -> RuntimeOverrides:
        timeout_ms = self._ctx_number(ctx, "scraper_timeout_ms")
        timeout_sec = self._default_timeout_sec
        if timeout_ms is not None:
            timeout_sec = max(0.2, float(timeout_ms) / 1000.0)

        max_retries = self._ctx_int(ctx, "scraper_max_retries")
        if max_retries is None:
            max_retries = self._default_max_retries

        backoff = self._ctx_int(ctx, "scraper_backoff_base_ms")
        if backoff is None:
            backoff = self._default_backoff_base_ms

        cache_ttl = self._ctx_int(ctx, "scraper_cache_ttl_sec")

        return RuntimeOverrides(
            timeout_sec=timeout_sec,
            max_retries=max(0, max_retries),
            backoff_base_ms=max(50, backoff),
            cache_ttl_sec=cache_ttl,
        )

    def _build_batch_metadata(
        self,
        results: List[ScraperSingleResult],
        ctx: Any,
        started_at: float,
    ) -> Dict[str, Any]:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        cache_hits = sum(1 for r in results if r.from_cache)
        total_retries = sum(max(0, r.retries) for r in results)
        errors = [r.error for r in results if r.error]

        meta: Dict[str, Any] = {
            "batch_size": len(results),
            "latency_ms": latency_ms,
            "cache_hits": cache_hits,
            "cache_misses": max(0, len(results) - cache_hits),
            "total_retries": total_retries,
        }
        if errors:
            meta["errors"] = errors
            meta["first_error"] = errors[0]

        for key in ("request_id", "org_id", "flow_name"):
            value = self._ctx_lookup(ctx, key)
            if value:
                meta[key] = value

        return meta

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
