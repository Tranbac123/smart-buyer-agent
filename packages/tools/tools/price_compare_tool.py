# packages/tools/tools/price_compare_tool.py
from __future__ import annotations

"""
PriceCompareTool
----------------
Thin, production-style adapter that calls the domain engine to fetch/merge
offers across shopping sites. It provides:

- Input validation & normalization (query, top_k, prefs, sites)
- Timeout & retry with exponential backoff
- A very light circuit breaker (fail-soft; avoids hammering broken sources)
- Stable output envelope: {"offers": [...], "metadata": {...}}

This tool is intentionally agnostic of HTTP; the engine handles its own I/O.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
import asyncio
import time
import math
import logging
import inspect

logger = logging.getLogger("quantumx.tools.price_compare")


# Engine abstraction (your concrete engine lives in search_core)
try:
    from packages.search_core.search_core.ecommerce.price_compare import PriceCompareEngine  # type: ignore
except Exception:  # pragma: no cover
    PriceCompareEngine = None  # type: ignore


class PriceCompareTool:
    """
    Adapter to the domain engine for price comparison across sites.

    Parameters
    ----------
    engine : object
        Instance with an `async def compare(query, top_k, prefs, sites)` method.
    timeout_s : float
        Per-attempt timeout (seconds) when awaiting the engine.
    max_retries : int
        Number of retries on transient failures (total attempts = 1 + max_retries).
    backoff_base : float
        Initial backoff in seconds; grows exponentially (base * 2^retry_idx).
    cb_threshold : int
        Open the circuit after this many consecutive failures.
    cb_cooldown_s : float
        Time (seconds) to keep the circuit open before allowing a new attempt.
    allow_sites / deny_sites : Optional[Sequence[str]]
        Optional filters to whitelist/blacklist sites at tool level.
    """
    def __init__(
        self,
        *,
        engine: Any | None = None,
        timeout_s: float = 8.0,
        max_retries: int = 2,
        backoff_base: float = 2.5,
        cb_threshold: int = 5,
        cb_cooldown_s: float = 30.0,
        allow_sites: Optional[Sequence[str]] = None,
        deny_sites: Optional[Sequence[str]] = None,
    ) -> None:
        if engine is None:
            if PriceCompareEngine is None:
                raise RuntimeError(
                    "PriceCompareTool: PriceCompareEngine is not available. "
                    "Ensure 'packages.search_core.search_core.ecommerce.price_compare' is importable."
                )
            engine = PriceCompareEngine()
        self.engine = engine
        self.timeout_s = float(timeout_s)
        self.max_retries = int(max_retries)
        self.backoff_base = float(backoff_base)
        # Circuit breaker (very light)
        self._cb_threshold = int(cb_threshold)
        self._cb_cooldown_s = float(cb_cooldown_s)
        self._cb_failures = 0
        self._cb_open_until = 0.0

        # Optional site policies
        self._allow_sites = set(map(_norm_site, allow_sites or []))
        self._deny_sites = set(map(_norm_site, deny_sites or []))

    # --------------------------------------------------------------------- #
    # Public API expected by ToolRegistry
    # --------------------------------------------------------------------- #
    async def call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the price-compare call with guardrails.
        Payload contract (MVP):
            {
              "query": str,
              "top_k": int,                 # optional, default 6
              "prefs": dict,                # optional
              "sites": list[str] | str      # optional site whitelist
            }
        Returns:
            {"offers": list[dict], "metadata": dict}
        Never raises; returns empty offers on failure with `metadata.error`.
        """
        t0 = time.perf_counter()
        # Circuit breaker check
        if self._circuit_open():
            note = "circuit_open"
            logger.warning("PriceCompareTool: circuit open; skipping call")
            return {"offers": [], "metadata": self._meta(t0, note=note, error=note)}
        # Validate & normalize inputs
        query, top_k, prefs, sites = self._parse_payload(payload)
        if not query:
            return {"offers": [], "metadata": self._meta(t0, note="empty_query")}
        # Apply tool-level site policy (allow/deny)
        sites = self._apply_site_policy(sites)

        # Attempt loop with exponential backoff
        attempts = 1 + max(0, self.max_retries)
        last_error: Optional[str] = None
        for attempt in range(attempts):
            try:
                # Engine may be async or sync; await if coroutine
                coro_or_res = self.engine.compare(query=query, top_k=top_k, prefs=prefs, sites=sites)
                if inspect.isawaitable(coro_or_res):
                    res = await asyncio.wait_for(coro_or_res, timeout=self.timeout_s)
                else:
                    # Discouraged: sync engine; still supported
                    logger.debug("PriceCompareTool: sync engine call (consider making it async)")
                    res = coro_or_res
                
                # Validate engine result shape
                offers, metadata = _coerce_engine_result(res)
                meta = self._meta(t0, sites=sites, attempts=attempt + 1, engine_meta=metadata)

                # Success → reset CB and return
                self._cb_record_success()
                return {"offers": offers, "metadata": meta}
            
            except asyncio.TimeoutError:
                last_error = "timeout"
                logger.warning("PriceCompareTool timeout (attempt %s/%s)", attempt + 1, attempts)
            except Exception as e: # transient or engine failure
                last_error = f"{type(e).__name__}: {e}"
                logger.exception("PriceCompareTool error: %s (attempt %s/%s)", last_error, attempt + 1, attempts)
            
            # Backoff (if more attempts remain)
            if attempt < attempts - 1:
                await asyncio.sleep(self._backoff_secs(attempt))
        # All attempts failed → open circuit, return fail-soft
        self._cb_record_failure()
        self._cb_maybe_open()
        return {"offers": [], "metadata": self._meta(
            t0,
            sites=sites,
            attempts=attempts,
            error=last_error or "unknown_error",
        )}

    # --------------------------------------------------------------------- #
    # Internals
    # --------------------------------------------------------------------- #
    def _parse_payload(self, payload: Dict[str, Any]) -> Tuple[str, int, Dict[str, Any], Optional[List[str]]]:
        query = str(payload.get("query", "")).strip()
        top_k = _clamp_int(payload.get("top_k"), default=6, lo=1, hi=50)
        prefs = dict(payload.get("prefs") or {})
        sites = _as_str_list(payload.get("sites"))
        return query, top_k, prefs, sites

    def _apply_site_policy(self, sites: Optional[List[str]]) -> Optional[List[str]]:
        if sites:
            s = {_norm_site(x) for x in sites if x}
        else:
            s = set()

        # deny has priority
        if self._deny_sites:
            s = {x for x in s if x not in self._deny_sites}

        # allow whitelist (if provided)
        if self._allow_sites:
            s = {x for x in (s or self._allow_sites) if x in self._allow_sites}

        return sorted(s) if s else (sorted(self._allow_sites) if self._allow_sites else None)

    def _backoff_secs(self, retry_idx: int) -> float:
        # Exponential backoff with jitter-lite
        base = self.backoff_base * (2 ** max(0, retry_idx))
        # cap to a sane max (e.g., 3s)
        return min(3.0, base)

    # ---- Circuit breaker (very light) ----

    def _circuit_open(self) -> bool:
        return time.monotonic() < self._cb_open_until

    def _cb_record_success(self) -> None:
        self._cb_failures = 0
        self._cb_open_until = 0.0

    def _cb_record_failure(self) -> None:
        self._cb_failures = min(self._cb_failures + 1, self._cb_threshold + 1)

    def _cb_maybe_open(self) -> None:
        if self._cb_failures >= self._cb_threshold:
            self._cb_open_until = time.monotonic() + self._cb_cooldown_s
            logger.warning("PriceCompareTool: circuit opened for %.1fs", self._cb_cooldown_s)

    # ---- Metadata ----

    def _meta(
        self,
        t0: float,
        *,
        note: Optional[str] = None,
        error: Optional[str] = None,
        sites: Optional[List[str]] = None,
        attempts: Optional[int] = None,
        engine_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta = {
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "attempts": attempts,
            "sites": sites or [],
            "note": note,
            "error": error,
            "circuit_open": self._circuit_open(),
        }
        if engine_meta:
            # Merge engine metadata shallowly
            meta["engine"] = engine_meta
        return {k: v for k, v in meta.items() if v is not None}


# -------------------------------------------------------------------------- #
# Helpers (pure functions)
# -------------------------------------------------------------------------- #

def _clamp_int(v: Any, *, default: int, lo: Optional[int] = None, hi: Optional[int] = None) -> int:
    try:
        x = int(v)
    except Exception:
        x = default
    if lo is not None:
        x = max(lo, x)
    if hi is not None:
        x = min(hi, x)
    return x


def _as_str_list(v: Any) -> Optional[List[str]]:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else None
    if isinstance(v, (list, tuple, set)):
        out = [str(x).strip() for x in v if str(x).strip()]
        return out or None
    return None


def _norm_site(v: Any) -> str:
    return str(v).strip().lower().replace(" ", "_")


def _coerce_engine_result(res: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Ensure the engine result has the expected shape.
    Returns (offers, metadata). Missing fields are replaced with defaults.
    """
    if not isinstance(res, dict):
        return [], {"error": f"engine_invalid_type:{type(res).__name__}"}
    offers = res.get("offers")
    if not isinstance(offers, list):
        offers = []
    offers = [x for x in offers if isinstance(x, dict)]

    meta = res.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    return offers, meta