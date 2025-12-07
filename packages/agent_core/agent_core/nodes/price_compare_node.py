# packages/agent_core/agent_core/nodes/price_compare_node.py
from __future__ import annotations

from typing import Dict, Any, List, Optional

from agent_core.agent_core.nodes.base import BaseNode
from packages.control_plane.control_plane.tool_registry import ToolRegistry
from packages.agent_core.agent_core.models import AgentState
from packages.control_plane.control_plane.core import (
    ControlPlane,
    PlanStep,
)
from packages.control_plane.helpers import (
    build_request_context,
    halt_state_with_error,
)


class PriceCompareNode(BaseNode):
    """
    Orchestrator node that calls the price-compare tool and writes results
    into AgentState.facts.
    """

    name = "price_compare"
    cost_per_call_tokens: int = 50

    def __init__(
        self,
        tools: ToolRegistry,
        *,
        tool_name: str = "price_compare",
        control_plane: ControlPlane | None = None,
    ) -> None:
        self.tools = tools
        self.tool_name = tool_name
        self.control_plane = control_plane

    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        facts = state.facts or {}
        state.facts = facts 
        query = str(facts.get("query") or state.query or "").strip()
        if len(query) < 2:
            state.facts["offers"] = []
            state.facts["price_compare_note"] = "query too short"
            return state

        top_k = _to_int(ctx.get("top_k"), default=6, lo=1, hi=50)
        prefs: Dict[str, Any] = dict(facts.get("prefs") or {})
        site_whitelist: Optional[List[str]] = _as_str_list(ctx.get("sites") or ctx.get("site"))

        payload: Dict[str, Any] = {"query": query, "top_k": top_k, "prefs": prefs}
        if site_whitelist:
            payload["sites"] = site_whitelist

        if self.control_plane:
            tool_payload = await self._execute_via_control_plane(state, ctx, payload)
            if tool_payload is None:
                state.facts["price_compare_note"] = "denied or failed by control_plane"
                return state
            offers = tool_payload.get("offers") or []
            metadata = tool_payload.get("metadata") or {}

            if not offers:
                state.facts["offers"] = []
                state.facts["price_compare_note"] = "no offers"
                return state
        else:
            offers, metadata = await self._execute_direct_tool(state, payload)

        offers_count = len(offers)
        state.facts["offers"] = offers
        state.facts["offers_count"] = offers_count
        state.metadata["offers_count"] = offers_count

        if metadata:
            metadata.setdefault("offers_count", offers_count)
            state.facts["price_compare_metadata"] = metadata
            state.metadata[f"{self.tool_name}_meta"] = metadata

        return state

    async def _execute_direct_tool(
        self,
        state: AgentState,
        payload: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        state.start_tool(self.tool_name)
        try:
            res = await self.tools.call(self.tool_name, payload)
        finally:
            state.end_tool()
        offers: List[Dict[str, Any]] = list(res.get("offers") or [])
        metadata = res.get("metadata") or {}
        return offers, metadata

    async def _execute_via_control_plane(
        self,
        state: AgentState,
        ctx: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self.control_plane:
            return None

        step = PlanStep(
            action="price_compare",
            parameters={
                "query": payload["query"],
                "max_items": payload["top_k"],
                "sites": payload.get("sites"),
            },
            context={"intent": "price_lookup"},
        )
        req_ctx = build_request_context(
            state,
            overrides={
                "request_id": ctx.get("request_id"),
                "user_id": ctx.get("user_id"),
                "org_id": ctx.get("org_id"),
                "role": ctx.get("role"),
                "channel": ctx.get("channel"),
                "flow_name": ctx.get("flow_name"),
            },
        )
        result = await self.control_plane.execute(step, req_ctx)
        if not result.success:
            halt_state_with_error(
                state,
                reason=result.extra.get("error_type") or "tool_error",
                message=result.error,
                tool=self.tool_name,
            )
            return None
        data = result.data or {}
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        items = data.get("items") or data.get("offers") or []
        metadata = data.get("metadata") or result.extra or {}
        return {"offers": items, "metadata": metadata}


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
