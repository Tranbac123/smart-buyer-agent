# apps/api/src/dependencies/tools_provider.py
from __future__ import annotations

from typing import Optional

from config.settings import settings
from packages.tools.tools.registry import ToolRegistry

# Optional tool imports are guarded so the API can still boot
# even if some tools are not installed/enabled.
try:
    from packages.tools.tools.price_compare_tool import PriceCompareTool  # type: ignore
except Exception:  # pragma: no cover
    PriceCompareTool = None  # type: ignore

try:
    from packages.tools.tools.decision_tool import DecisionTool  # type: ignore
except Exception:  # pragma: no cover
    DecisionTool = None  # type: ignore

try:
    from packages.tools.tools.scraper_tool import ScraperTool  # type: ignore
except Exception:  # pragma: no cover
    ScraperTool = None  # type: ignore

try:
    from packages.tools.tools.search_web import WebSearchTool  # type: ignore
except Exception:  # pragma: no cover
    WebSearchTool = None  # type: ignore

# Process-wide singleton. FastAPI will call our dependency per-request,
# but we only build the registry once.
_TOOL_REGISTRY: Optional[ToolRegistry] = None


def _register_core_tools(reg: ToolRegistry) -> None:
    """
    Register baseline tools used by the Smart-Buyer vertical slice.
    Idempotent by construction (ToolRegistry.register should overwrite or raise).
    """
    feats = getattr(settings, "FEATURES", None)

    # Price compare (web search + site adapters)
    if PriceCompareTool is not None and (not feats or feats.enable_smart_buyer):
        if "price_compare" not in reg._tools:  # access internal map deliberately to avoid double logs
            reg.register("price_compare", PriceCompareTool())

    # Decision scorer (criteria-based ranking + explanation bundle)
    if DecisionTool is not None and (not feats or feats.enable_smart_buyer):
        if "decision_score" not in reg._tools:
            reg.register("decision_score", DecisionTool())

    if ScraperTool is not None and (not feats or feats.enable_smart_buyer):
        if "scraper_fetch" not in reg._tools:
            reg.register("scraper_fetch", ScraperTool())

    if WebSearchTool is not None and (not feats or feats.enable_smart_buyer):
        if "web_search" not in reg._tools:
            reg.register("web_search", WebSearchTool())


def get_tool_registry() -> ToolRegistry:
    """
    FastAPI dependency provider for a shared ToolRegistry.

    Behavior:
      - Builds a single registry on first use.
      - Registers core tools based on feature flags.
      - Safe to call multiple times (idempotent).
    """
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is None:
        reg = ToolRegistry()
        _register_core_tools(reg)
        _TOOL_REGISTRY = reg
    return _TOOL_REGISTRY


# ---- Utilities useful in tests or dynamic environments ----

def reset_tool_registry() -> None:
    """
    Clear the global registry so tests can rebuild a clean instance.
    """
    global _TOOL_REGISTRY
    _TOOL_REGISTRY = None


def register_tool(name: str, tool: object) -> None:
    """
    Programmatically add/override a tool at runtime (e.g., in tests).
    If the registry hasn't been created yet, it will be initialized first.
    """
    reg = get_tool_registry()
    reg.register(name, tool)
