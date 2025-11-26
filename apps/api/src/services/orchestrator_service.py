# apps/api/src/orchestrator/orchestrator_service.py
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from packages.agent_core.agent_core.models import AgentState
from packages.tools.tools.registry import ToolRegistry
from packages.llm_client.llm_client.base import ILLMClient  # Protocol-like
from packages.memory_core.memory_core.base import IMemory  # optional
from router.flows.smart_buyer_flow import SmartBuyerFlow

logger = logging.getLogger("quantumx.orchestrator")


@dataclass(slots=True)
class OrchestratorService:
    """
    Thin orchestration layer that wires API inputs to Agent flows.

    Responsibilities:
    - Input validation / shaping (query, prefs, criteria)
    - Build AgentState and flow context
    - Execute the flow with timeout
    - Normalize outputs & attach telemetry metadata
    - Fail-soft on errors/timeouts (never crash the API)
    """

    memory: Optional[IMemory] = None
    default_timeout_s: float = 20.0
    default_budget_tokens: int = 16_000
    max_steps: int = 8  # reserved for future guards/policies

    # ------------- Public API -------------

    async def run_smart_buyer(
        self,
        *,
        query: str,
        top_k: int,
        prefs: Optional[Dict[str, Any]],
        criteria: Optional[List[Dict[str, Any]]],
        tools: ToolRegistry,
        llm: ILLMClient,
        http: Any,  # reserved for flows/tools that need an HTTP client
        request_id: str,
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute the SmartBuyer vertical slice (PriceCompare -> Decision -> Explain -> Finalize).
        Returns a stable JSON envelope even on failures.
        """
        q = (query or "").strip()
        if len(q) < 2:
            return self._error_response(
                request_id,
                reason="query too short",
                http_status=None,
                extra={"offers": [], "scoring": _empty_scoring(), "explanation": _explain_summary("query too short")},
            )

        t0 = time.perf_counter()
        # Build initial state
        state = AgentState(
            session_id=request_id,
            query=q,
            facts={
                "prefs": dict(prefs or {}),
                "criteria": list(criteria or []),
            },
            logs=[],
            budget_tokens=self.default_budget_tokens,
            done=False,
        )

        # Flow + context
        flow = SmartBuyerFlow(tools=tools, llm=llm, memory=self.memory, default_timeout_s=timeout_s or self.default_timeout_s)
        ctx: Dict[str, Any] = {
            "top_k": int(top_k),
            "request_id": request_id,
            "timeout_s": float(timeout_s or self.default_timeout_s),
        }

        try:
            result = await asyncio.wait_for(flow.run(state, ctx), timeout=ctx["timeout_s"])
        except asyncio.TimeoutError:
            logger.warning("smart_buyer timeout request_id=%s", request_id)
            return self._error_response(request_id, reason="timeout")
        except asyncio.CancelledError:
            logger.error("smart_buyer cancelled request_id=%s", request_id)
            raise  # propagate cancellation to server (graceful shutdown)
        except Exception as e:  # fail-soft
            logger.exception("smart_buyer error request_id=%s: %s", request_id, e)
            return self._error_response(request_id, reason=type(e).__name__)

        # Attach metadata
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if isinstance(result, dict):
            result.setdefault("metadata", {})
            result["metadata"]["request_id"] = request_id
            result["metadata"]["latency_ms"] = latency_ms
            result["metadata"]["flow"] = "smart_buyer"
        else:
            # Extremely defensive: should not happen, but keep API stable.
            result = {
                "offers": [],
                "scoring": _empty_scoring(),
                "explanation": _explain_summary("invalid flow result"),
                "metadata": {"request_id": request_id, "latency_ms": latency_ms, "flow": "smart_buyer"},
            }

        return result

    # ------------- Internals -------------

    def _error_response(
        self,
        request_id: str,
        *,
        reason: str,
        http_status: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Produce a stable error envelope. `http_status` is intentionally unused here
        (the router may still return 200 to surface partial results in UI).
        """
        payload = {
            "offers": [],
            "scoring": _empty_scoring(),
            "explanation": _explain_summary(reason),
            "metadata": {"request_id": request_id, "error": reason, "flow": "smart_buyer"},
        }
        if extra:
            # Minimal, safe merge
            for k in ("offers", "scoring", "explanation"):
                if k in extra:
                    payload[k] = extra[k]
        return payload


# ---------- Small helpers (pure) ----------

def _empty_scoring() -> Dict[str, Any]:
    return {"confidence": 0.0, "option_scores": [], "best": None}


def _explain_summary(msg: str) -> Dict[str, Any]:
    return {
        "winner": None,
        "confidence": 0.0,
        "best_by_criterion": {},
        "tradeoffs": [],
        "per_option": [],
        "summary": msg,
    }
