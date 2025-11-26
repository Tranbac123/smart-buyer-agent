# packages/agent_core/agent_core/nodes/price_compare.py
from __future__ import annotations

from typing import Dict, Any, List, Optional

from agent_core.agent_core.nodes.base import BaseNode
from packages.tools.tools.registry import ToolRegistry
from packages.agent_core.agent_core.models import AgentState

class PriceCompareNode(BaseNode):
    """
    Orchestrator node that calls the price-compare tool and writes results
    into AgentState.facts.

    Responsibilities:
    - Validate/normalize inputs (query, top_k, prefs, site filters)
    - Call ToolRegistry("price_compare")
    - Store offers + metadata in state.facts
    - Fail-soft on errors (pipeline continues)
    """
    name = "price_compare"
    cost_per_call_tokens: int = 50

    def __init__(self, tools: ToolRegistry, *, tool_name: str = "price_compare") -> None:
        self.tools = tools
        self.tool_name = tool_name
    
    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        query = (state.facts or {}).get("query")
        if len(query) < 2:
            # Keep pipeline alive; downstream nodes will handle empty offers.
            state.facts["offers"] = []
            state.facts["price_compare_note"] = "query too short"
            return state
        
        # ctx options with safe defaults
        top_k = _to_int(ctx.get("top_k"), default=6, lo=1, hi=50)
        prefs: Dict[str, Any] = dict((state.facts or {}).get("prefs") or {})
        site_whilelist: Optional[List[str]] = _as_str_list(ctx.get("site")) # e.g., ["shopee", "lazada"]

        payload: Dict[str, Any] = {"query": query, "top_k": top_k, "prefs": prefs}
        if site_whilelist:
            payload["site"] = site_whilelist

        # --- Tool call ---
        # Expected tool contract (MVP):
        #   input : {"query": str, "top_k": int, "prefs": dict, "sites": [str]?}
        #   output: {"offers": [...], "metadata": {...}?}
        res = await self.tools.call(self.tool_name, payload)

        offers: List[Dict[str, Any]] = list(res.get("offers") or [])
        state.facts["offers"] = offers

        meta = res.get("metadata")
        if meta:
            state.facts["price_compare_metadata"] = meta
        
        # Hint: you can cache some derived facts for later nodes (optional)
        state.facts["offers_count"] = len(offers)

        return state

# healpers

def _to_int(v: Any, *, default: int, lo: Optional[int] = None, hi: Optional[int] = None) -> int:
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
    if isinstance(v, (list, tuple)):
        out = [str(x).strip() for x in v if str(x).strip()]
        return out or None
    return None
