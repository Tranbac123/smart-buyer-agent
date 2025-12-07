# apps/api/src/services/smart_buyer_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
import asyncio
import time
import logging
from contextlib import asynccontextmanager

from packages.control_plane.control_plane.tool_registry import ToolRegistry
from packages.agent_core.agent_core.models import AgentState
from apps.api.src.router.flows.smart_buyer_flow import SmartBuyerFlow
from apps.api.src.services.smart_buyer_formatter import render_smart_buyer_summary
from packages.control_plane.control_plane.core import ControlPlane

logger = logging.getLogger("quantumx.smart_buyer_service")


class SmartBuyerService:
    """
    State-first Smart Buyer service.
    - Builds the initial AgentState and context
    - Runs the SmartBuyerFlow (state-first, guarded loop inside the flow)
    - Applies outer timeout/step policy and fail-soft response envelope
    """

    def __init__(
        self,
        *,
        tools: ToolRegistry,
        llm: Any | None,
        memory: Any | None = None,
        control_plane: ControlPlane | None = None,
        default_top_k: int = 5,
        default_timeout_s: float = 20.0,
        default_max_steps: int = 8,
    ) -> None:
        self.tools = tools
        self.llm = llm
        self.memory = memory
        self.control_plane = control_plane
        self.default_top_k = int(default_top_k)
        self.default_timeout_s = float(default_timeout_s)
        self.default_max_steps = int(default_max_steps)

    async def run(
        self,
        *,
        query: str,
        prefs: Optional[Dict[str, Any]] = None,
        criteria: Optional[List[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
        sites: Optional[List[str]] = None,
        request_id: Optional[str] = None,
        timeout_s: Optional[float] = None,
        max_steps: Optional[int] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        role: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the Smart Buyer reasoning flow and return a stable response.
        """
        t0 = time.perf_counter()
        q = (query or "").strip()
        if not q:
            return self._fail_soft(
                "empty_query",
                t0,
                request_id=request_id,
                note="Query is empty",
            )

        # Build state-first inputs
        state = AgentState(
            session_id=request_id or "smart-buyer",
            query=q,
            facts={
                "query": q,
                "prefs": dict(prefs or {}),
                "criteria": list(criteria or []),
            },
            log=[],
            budget_token=16000,
            done=False,
        )
        state.metadata.update(
            {
                "request_id": request_id,
                "user_id": user_id,
                "org_id": org_id,
                "role": role,
                "channel": channel,
                "flow_name": "smart_buyer",
            }
        )
        ctx = {
            "top_k": int(top_k or self.default_top_k),
            "request_id": request_id or "smart-buyer",
            "timeout_s": float(timeout_s or self.default_timeout_s),
            "max_steps": int(max_steps or self.default_max_steps),
            "sites": sites or None,
            "user_id": user_id,
            "org_id": org_id,
            "role": role,
            "channel": channel,
            "flow_name": "smart_buyer",
        }

        flow = SmartBuyerFlow(
            tools=self.tools,
            llm=self.llm,
            memory=self.memory,
            control_plane=self.control_plane,
            default_timeout_s=ctx["timeout_s"],
            default_max_steps=ctx["max_steps"],
        )

        try:
            async with self._overall_timeout(ctx["timeout_s"]):
                result = await flow.run(state, ctx)
        except asyncio.TimeoutError:
            logger.warning("SmartBuyer overall timeout (%.2fs)", ctx["timeout_s"])
            return self._fail_soft(
                "timeout",
                t0,
                request_id=request_id,
                note=f"Overall timeout {ctx['timeout_s']}s",
            )
        except Exception as e:
            logger.exception("SmartBuyer flow error: %s", e)
            return self._fail_soft(
                "error",
                t0,
                request_id=request_id,
                note=f"{type(e).__name__}: {e}",
            )

        # Ensure stable envelope
        return self._normalize_response(result, t0, request_id=request_id, query=q)

    # --------------------------------------------------------------------- #
    # Internals
    # --------------------------------------------------------------------- #

    @asynccontextmanager
    async def _overall_timeout(self, seconds: float):
        task = asyncio.current_task()
        if not task or seconds <= 0:
            yield
            return
        try:
            yield
        finally:
            # nothing to cancel here; top-level timeout is applied by caller via asyncio.wait_for if needed
            ...

    def _normalize_response(
        self,
        result: Dict[str, Any],
        t0: float,
        *,
        request_id: Optional[str],
        query: str,
    ) -> Dict[str, Any]:
        offers = result.get("offers") if isinstance(result, dict) else None
        scoring = result.get("scoring") if isinstance(result, dict) else None
        explanation = result.get("explanation") if isinstance(result, dict) else None
        metadata = result.get("metadata") if isinstance(result, dict) else None

        if not isinstance(offers, list):
            offers = []
        if not isinstance(scoring, dict):
            scoring = {"option_scores": [], "best": None, "confidence": 0.0}
        if not isinstance(explanation, dict):
            explanation = {"summary": "No explanation", "tradeoffs": [], "best_by_criterion": {}, "per_option": []}
        if not isinstance(metadata, dict):
            metadata = {}

        metadata = {
            **metadata,
            "request_id": request_id,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "service": "smart_buyer",
        }

        normalized = {
            "offers": offers,
            "scoring": scoring,
            "explanation": explanation,
            "metadata": metadata,
        }
        summary_text = render_smart_buyer_summary({**normalized, "query": query})
        normalized["summary_text"] = summary_text
        normalized["query"] = query
        return normalized

    def _fail_soft(
        self,
        err_code: str,
        t0: float,
        *,
        request_id: Optional[str],
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "offers": [],
            "scoring": {"option_scores": [], "best": None, "confidence": 0.0},
            "explanation": {
                "summary": "No results available",
                "tradeoffs": [],
                "best_by_criterion": {},
                "per_option": [],
                "note": note or err_code,
            },
            "metadata": {
                "error": err_code,
                "request_id": request_id,
                "latency_ms": int((time.perf_counter() - t0) * 1000),
                "service": "smart_buyer",
            },
        }
        payload["summary_text"] = render_smart_buyer_summary(payload)
        return payload
