from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_core.agent_core.nodes.base import BaseNode
from packages.agent_core.agent_core.models import AgentState
from packages.control_plane.control_plane.core import ControlPlane, PlanStep
from packages.control_plane.control_plane.tool_registry import ToolRegistry
from packages.control_plane.helpers import build_request_context, halt_state_with_error


class ScraperNode(BaseNode):
    """
    Node that calls the scraper_fetch tool to run arbitrary HTTP requests.

    Behavior
    --------
    * Looks for `scraper_requests` in AgentState.facts or flow ctx.
    * If present, executes the scraper tool (via ControlPlane when available).
    * Writes normalized results and metadata back to AgentState.facts/metadata.
    * Fails softly (halts state) when the control plane reports an error.
    """

    name = "scraper_fetch"
    cost_per_call_tokens: int = 20

    def __init__(
        self,
        tools: ToolRegistry,
        *,
        tool_name: str = "scraper_fetch",
        control_plane: ControlPlane | None = None,
    ) -> None:
        self.tools = tools
        self.tool_name = tool_name
        self.control_plane = control_plane

    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        requests = self._collect_requests(state, ctx)
        if not requests:
            return state

        if self.control_plane:
            payload = await self._execute_via_control_plane(state, ctx, requests)
        else:
            payload = await self._execute_direct_tool(state, ctx, requests)

        if payload is None:
            return state

        results = payload.get("results") or []
        metadata = payload.get("metadata") or {}

        state.facts["scraper_results"] = results
        if metadata:
            state.facts["scraper_metadata"] = metadata
            state.metadata[f"{self.tool_name}_meta"] = metadata
            state.metadata["scraper_results_count"] = len(results)

        return state

    def _collect_requests(self, state: AgentState, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates: List[Any] = []
        facts_requests = (state.facts or {}).get("scraper_requests")
        if isinstance(facts_requests, list):
            candidates.extend(facts_requests)
        ctx_requests = ctx.get("scraper_requests")
        if isinstance(ctx_requests, list):
            candidates.extend(ctx_requests)

        normalized: List[Dict[str, Any]] = []
        for item in candidates:
            if isinstance(item, dict) and "url" in item:
                normalized.append(dict(item))
        return normalized

    async def _execute_direct_tool(
        self,
        state: AgentState,
        ctx: Dict[str, Any],
        requests: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"requests": requests, "_ctx": ctx}
        state.start_tool(self.tool_name)
        try:
            return await self.tools.call(self.tool_name, payload)
        finally:
            state.end_tool()

    async def _execute_via_control_plane(
        self,
        state: AgentState,
        ctx: Dict[str, Any],
        requests: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self.control_plane:
            return None

        step = PlanStep(
            action=self.tool_name,
            parameters={"requests": requests},
            context={"intent": "scraper_fetch", "batch_size": len(requests)},
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
        metadata = data.get("metadata") or result.extra or {}
        return {"results": data.get("results", []), "metadata": metadata}


