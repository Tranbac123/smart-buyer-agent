# packages/search_core/search_core/ecommerce/price_compare.py
from __future__ import annotations

"""
PriceCompareEngine (MVP+)
-------------------------
Fetches offers from multiple e-commerce sources (site adapters), then
normalizes, canonicalizes, and deduplicates them to produce a clean list
suitable for decision/scoring.

Key features:
- Async fan-out to site adapters with per-adapter fail-soft handling
- Lightweight canonicalization (brand/model/variant) from titles
- Currency unification (to VND by default) + effective_price (price + fees)
- De-duplication by canonical key with simple merge rules
- Stable, minimal output shape for downstream nodes

This file is intentionally self-contained (no external HTTP) and ships two
mock adapters for Shopee/Lazada so your stack can run end-to-end today.
Replace mocks with real adapters later (HTTP scraping/APIs) while keeping
the engine contract intact.

Contract
--------
async def compare(
    query: str,
    top_k: int = 6,
    prefs: dict | None = None,
    sites: list[str] | None = None,
) -> dict:
    return {
      "offers": [ ... normalized offer dicts ... ],
      "metadata": {
        "engine": "v1",
        "queried_sites": [...],
        "errors": {site: "..."}  # per-site error messages (optional)
      }
    }
"""


from typing import Optional, List, Dict, Any
import time
import asyncio

class PriceCompareEngine:
    """
    Orchestrates site adapters, normalization, and de-duplication.
    """
    def __init__(
        self,
        *,
        default_sites: Optional[List[str]] = None,
        per_site_timeout_s: float = 6.0,
        currency: str = "VND",
    ) -> None:
        self.default_sites = default_sites or ["shopee", "lazada"]
        self.per_site_timeout_s = float(per_site_timeout_s)
        self.currency = currency
    
    async def compare(
        self,
        *,
        query: str,
        top_k: int = 6,
        prefs: Dict[str, Any] | None = None,
        sites: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        query = (query or "").strip()
        if not query:
            return {"offers": [], "metadata": {"engine": "v1", "note" : "empty query"}}
        k = _clamp_int(top_k, 1, 50)
        sites = _normalize_sites(sites or self.default_sites)

        # 1) Fan-out to site adapters
        results: Dict[str, List[Dict[str, Any]]] = {}
        errors: Dict[str, str] = {}

        async def _run_site(site: str) -> None:
            adapter = get_site_adapter(site)
            if adapter is None:
                errors[site] = "no-adapter"
                results[site] = []
                return
            try:
                res = await asyncio.wait_for(
                    adapter.search(query=query, prefs=prefs or {}, limit=k),
                    timeout=self.per_site_timeout_s,
                )
                results[site] = res or []
            except asyncio.TimeoutError:
                errors[site] = "timeout"
                results[site] = []
            except Exception as e:
                errors[site] = f"{type(e).__name__}: {e}"
                results[site] = []
        await asyncio.gather(*[_run_site(s) for s in sites])
            
        # 2) Normalize & canonicalize
        raw_offers: List[Dict[str, Any]] = []
        for site, site_offers in results.items():
            for offer in site_offers:
                norm = _normalize_offer(site, offer, target_currency=self.currency)
                if norm is not None:
                    raw_offers.append(norm)
        # 3) Deduplicate by canonical key (brand, model, variant)
        fused_offers = _fuse_duplicates(raw_offers)
        # 4) Sort by effective price / availability / rating (simple heuristic)
        fused_offers.sort(key=lambda x: (not bool(x.get("in_stock", True)), float(x.get("effective_price", 1e18)), -float(x.get("seller_rating", 0.0))))
        # 5) Truncate to top_k
        offers_out = fused_offers[:k]

        meta = {
            "engine": "v1",
            "queried_sites": sites,
            "latency_s": int((time.perf_counter() - t0) * 1000),
        }
        if errors:
            meta["errors"] = errors
        return {"offers": offers_out, "metadata": meta}


class PriceCompare:
    """
    Backwards-compatible wrapper used by orchestrators that expect a simple
    `compare_prices` coroutine.
    """

    def __init__(self, **engine_kwargs):
        self._engine = PriceCompareEngine(**engine_kwargs)

    async def compare_prices(
        self,
        *,
        product_name: str,
        sites: Optional[List[str]] = None,
        top_k: int = 6,
        prefs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await self._engine.compare(
            query=product_name,
            top_k=top_k,
            prefs=prefs or {},
            sites=sites,
        )

# --------------------------------------------------------------------------- #
# Site Adapter Abstraction (MVP: mock adapters)
# --------------------------------------------------------------------------- #


class SiteAdapter:
    """
    Minimal interface each site adapter should implement:
      async def search(self, query: str, prefs: dict, limit: int) -> List[Dict[str, Any]]
    Return a list of raw offer dicts (adapter-specific shape); the engine will
    normalize/canonicalize them.
    """

    site: str = "generic"

    async def search(self, *, query: str, prefs: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:  # pragma: no cover - override
        raise NotImplementedError


class ShopeeMockAdapter(SiteAdapter):
    site = "shopee"

    async def search(self, *, query: str, prefs: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.05)  # simulate I/O
        out: List[Dict[str, Any]] = []
        base = _hash_bias(query + self.site)
        for i in range(max(1, min(limit, 50))):
            price = 2_000_000 + (base + i) * 17_500 % 800_000
            out.append(
                {
                    "title": f"{query} Official Store {i+1}",
                    "price": round(price, 2),
                    "currency": "VND",
                    "url": f"https://shopee.vn/{_slug(query)}-{i+1}",
                    "shipping_fee": 0 if i % 3 == 0 else 15_000,
                    "in_stock": i % 9 != 0,
                    "seller": "Shopee Mall" if i % 2 == 0 else "Third-Party",
                    "seller_rating": 4.6 - (i % 3) * 0.1,
                    "warranty_months": 12 if i % 2 == 0 else 6,
                    "return_policy": "7 days",
                    "attributes": {"color": "black" if i % 2 == 0 else "blue", "capacity": "128GB" if i % 3 else "256GB"},
                }
            )
        return out


class LazadaMockAdapter(SiteAdapter):
    site = "lazada"

    async def search(self, *, query: str, prefs: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.06)  # simulate I/O
        out: List[Dict[str, Any]] = []
        base = _hash_bias(query + self.site)
        for i in range(max(1, min(limit, 50))):
            price = 1_950_000 + (base + i) * 19_900 % 900_000
            out.append(
                {
                    "name": f"{query} (Flagship) {i+1}",
                    "amount": round(price, 2),
                    "ccy": "VND",
                    "link": f"https://lazada.vn/{_slug(query)}/{i+1}",
                    "ship_fee": 12_000 if i % 4 == 0 else 0,
                    "available": True if i % 5 else False,
                    "seller": "LazMall" if i % 2 == 1 else "Trusted Seller",
                    "rating": 4.7 - (i % 4) * 0.15,
                    "warranty": "12m",
                    "return": "15 days",
                    "attrs": {"color": "black", "capacity": "128GB" if i % 2 else "256GB"},
                }
            )
        return out


def get_site_adapter(site: str) -> Optional[SiteAdapter]:
    site = (site or "").strip().lower()
    if site == "shopee":
        return ShopeeMockAdapter()
    if site == "lazada":
        return LazadaMockAdapter()
    # Add your real adapters here:
    # if site == "tiki": return TikiAdapter()
    return None


# --------------------------------------------------------------------------- #
# Normalization / Canonicalization
# --------------------------------------------------------------------------- #


def _normalize_offer(site: str, raw: Dict[str, Any], *, target_currency: str) -> Optional[Dict[str, Any]]:
    """
    Map raw adapter payloads to a stable normalized offer.

    Output fields (typical):
      id, site, title, price, currency, url, shipping, in_stock, seller_rating,
      warranty, return_policy, attributes, canonical (brand/model/variant), effective_price
    """
    try:
        site_l = site.lower()

        if site_l == "shopee":
            title = str(raw.get("title", "")).strip()
            price = _to_float(raw.get("price"))
            currency = str(raw.get("currency", target_currency) or target_currency)
            url = str(raw.get("url", ""))
            shipping_fee = _to_float(raw.get("shipping_fee", 0.0)) or 0.0
            in_stock = bool(raw.get("in_stock", True))
            seller_rating = _to_float(raw.get("seller_rating", 0.0)) or 0.0
            warranty = str(raw.get("warranty_months", "") or "")
            return_policy = str(raw.get("return_policy", "") or "")
            attrs = dict(raw.get("attributes") or {})

        elif site_l == "lazada":
            title = str(raw.get("name", "")).strip()
            price = _to_float(raw.get("amount"))
            currency = str(raw.get("ccy", target_currency) or target_currency)
            url = str(raw.get("link", ""))
            shipping_fee = _to_float(raw.get("ship_fee", 0.0)) or 0.0
            in_stock = bool(raw.get("available", True))
            seller_rating = _to_float(raw.get("rating", 0.0)) or 0.0
            warranty = str(raw.get("warranty", "") or "")
            return_policy = str(raw.get("return", "") or "")
            attrs = dict(raw.get("attrs") or {})

        else:
            # Unknown site schema; try generic mapping
            title = str(raw.get("title") or raw.get("name") or "").strip()
            price = _to_float(raw.get("price") or raw.get("amount"))
            currency = str(raw.get("currency") or raw.get("ccy") or target_currency)
            url = str(raw.get("url") or raw.get("link") or "")
            shipping_fee = _to_float(raw.get("shipping") or raw.get("ship_fee") or 0.0) or 0.0
            in_stock = bool(raw.get("in_stock") if "in_stock" in raw else raw.get("available", True))
            seller_rating = _to_float(raw.get("seller_rating") or raw.get("rating") or 0.0) or 0.0
            warranty = str(raw.get("warranty") or raw.get("warranty_months") or "")
            return_policy = str(raw.get("return_policy") or raw.get("return") or "")
            attrs = dict(raw.get("attributes") or raw.get("attrs") or {})

        if not title or price is None:
            return None

        # Currency normalize (very basic; assumes VND target)
        price_vnd, fx_note = _to_vnd(price, currency)
        effective_price = price_vnd + max(0.0, float(shipping_fee))

        canon = _canonicalize_title(title, attrs)

        # Compose normalized offer
        offer = {
            "id": f"{site_l}-{_slug(title)[:40]}",
            "site": site_l,
            "title": title,
            "price": round(price_vnd, 2),
            "currency": "VND",
            "url": url,
            "shipping": shipping_fee if shipping_fee else 0.0,
            "effective_price": round(effective_price, 2),
            "in_stock": in_stock,
            "seller_rating": round(seller_rating, 2),
            "warranty": warranty,
            "return_policy": return_policy,
            "attributes": attrs,
            "canonical": canon,  # {"brand","model","variant"}
        }
        if fx_note:
            offer["fx_note"] = fx_note
        return offer
    except Exception:
        return None


def _canonicalize_title(title: str, attrs: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Very light heuristic canonicalization:
      - brand: first token capitalized (if looks like a brand)
      - model: next 1–2 tokens until parentheses or variant terms
      - variant: capacity/color if present in attrs or title
    Replace with a proper NER/dictionary-based matcher later.
    """
    t = title.strip()
    tokens = [tok for tok in _split_tokens(t) if tok]

    brand = None
    model = None
    variant = None

    if tokens:
        brand = tokens[0].capitalize()
    if len(tokens) >= 2:
        # stop at parentheses / dash or a capacity pattern
        cut = len(tokens)
        for i, tok in enumerate(tokens[1:], start=1):
            low = tok.lower()
            if low in {"-", "(", "[", "|"} or _looks_capacity(low):
                cut = i
                break
        model = " ".join(tokens[1:cut]) or None

    # Try capacity from attrs first, then from title
    capacity = str(attrs.get("capacity", "")).upper()
    if not capacity or not _looks_capacity(capacity.lower()):
        for tok in tokens:
            if _looks_capacity(tok.lower()):
                capacity = tok.upper()
                break
    color = str(attrs.get("color", "")).lower()
    if capacity and color:
        variant = f"{capacity} {color}"
    elif capacity:
        variant = capacity
    elif color:
        variant = color

    # Compact brand/model (avoid silly artifacts)
    brand = brand or None
    model = model or None
    variant = variant or None

    return {"brand": brand, "model": model, "variant": variant}


def _fuse_duplicates(offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge duplicate offers that refer to the same canonical product.
    Merge policy (simple):
      - group key: (brand|?, model|?, variant|?) normalized to lowercase
      - keep the best (lowest effective_price), but aggregate seller_rating max
      - keep earliest non-empty warranty/return_policy
      - keep a union of attributes (shallow)
      - keep a list of sources in `sources`
    """
    buckets: Dict[Tuple[Optional[str], Optional[str], Optional[str]], List[Dict[str, Any]]] = {}
    for o in offers:
        c = o.get("canonical") or {}
        key = (
            _norm(c.get("brand")),
            _norm(c.get("model")),
            _norm(c.get("variant")),
        )
        buckets.setdefault(key, []).append(o)

    fused: List[Dict[str, Any]] = []
    for _, group in buckets.items():
        if not group:
            continue
        # Pick best by effective_price, tie-break by seller_rating desc
        best = sorted(group, key=lambda x: (float(x.get("effective_price", 1e18)), -float(x.get("seller_rating", 0.0))))[0]
        merged = dict(best)

        # Aggregate seller_rating (max), warranty/return first non-empty from any
        merged["seller_rating"] = max(float(x.get("seller_rating", 0.0)) for x in group)
        for field in ("warranty", "return_policy"):
            if not merged.get(field):
                for x in group:
                    if x.get(field):
                        merged[field] = x[field]
                        break

        # Merge attributes (shallow)
        attrs: Dict[str, Any] = {}
        for x in group:
            for k, v in (x.get("attributes") or {}).items():
                attrs.setdefault(k, v)
        merged["attributes"] = attrs

        # Sources
        merged["sources"] = sorted({x.get("site") for x in group if x.get("site")})

        fused.append(merged)

    return fused


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def _normalize_sites(sites: List[str]) -> List[str]:
    out = []
    for s in sites:
        s = (s or "").strip().lower()
        if s:
            out.append(s)
    # keep order but unique
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def _clamp_int(v: Any, lo: int, hi: int) -> int:
    try:
        x = int(v)
    except Exception:
        x = lo
    return max(lo, min(hi, x))


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _to_vnd(amount: float, currency: str) -> Tuple[float, Optional[str]]:
    """
    Placeholder FX to VND. Replace with real rates later.
    """
    cur = (currency or "VND").upper()
    if cur == "VND":
        return float(amount), None
    # toy rates
    rates = {"USD": 25_000.0, "EUR": 27_000.0, "SGD": 18_500.0}
    rate = rates.get(cur)
    if rate is None:
        # Unknown -> assume already VND
        return float(amount), f"unknown_ccy:{cur}"
    return float(amount) * rate, f"fx:{cur}->VND@{rate:g}"


def _split_tokens(s: str) -> List[str]:
    buf = []
    cur = []
    for ch in s:
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                buf.append("".join(cur))
                cur = []
            if ch in "-()[]|":
                buf.append(ch)
    if cur:
        buf.append("".join(cur))
    return buf


def _looks_capacity(tok: str) -> bool:
    # 64gb, 128gb, 256gb, 1tb etc.
    tok = tok.strip().lower()
    if tok.endswith("gb"):
        return tok[:-2].isdigit()
    if tok.endswith("tb"):
        return tok[:-2].isdigit()
    return False


def _slug(s: str) -> str:
    return "-".join(t.lower() for t in _split_tokens(s) if t)


def _norm(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip().lower()
    return s or None


def _hash_bias(s: str) -> int:
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h