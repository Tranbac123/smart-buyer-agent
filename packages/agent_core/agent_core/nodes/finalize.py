# packages/agent_core/agent_core/nodes/finalize.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_core.agent_core.models import AgentState
from agent_core.agent_core.nodes.base import BaseNode


class FinalizeNode(BaseNode):
    """
    Final node that assembles a stable response envelope and marks the AgentState as done.

    Responsibilities:
    - Collect offers/scoring/explanation from state.facts
    - Normalize minimal fields (winner/summary) if missing
    - Attach metadata (step_index, request_id, counts, etc.)
    - Call state.mark_done(output)
    """

    name = "finalize"

    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        offers: List[Dict[str, Any]] = _as_list_of_dicts(state.facts.get("offers"))
        scoring: Dict[str, Any] = _as_dict(state.facts.get("scoring"))
        explanation: Dict[str, Any] = _as_dict(state.facts.get("explanation"))

        # Winner fallback
        if explanation.get("winner") is None:
            explanation["winner"] = _infer_winner(scoring)

        # Summary fallback
        if not explanation.get("summary"):
            explanation["summary"] = _auto_summary(
                winner=explanation.get("winner"),
                offers_count=len(offers),
                confidence=float(scoring.get("confidence", 0.0)),
            )

        # Build metadata
        metadata: Dict[str, Any] = {
            "step_index": state.step_index,
            "offers_count": len(offers),
        }
        # propagate request_id (if router/orchestrator injected it)
        rid = ctx.get("request_id")
        if isinstance(rid, str) and rid:
            metadata["request_id"] = rid
        # keep any latency that upstream may have added in flow
        if isinstance(state.output, dict):
            latency = state.output.get("metadata", {}).get("latency_ms")
            if latency is not None:
                metadata["latency_ms"] = latency

        output = {
            "offers": offers,
            "scoring": scoring,
            "explanation": explanation,
            "metadata": metadata,
        }

        state.mark_done(output)
        return state


# -------------------------
# Helpers (pure functions)
# -------------------------

def _as_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list_of_dicts(v: Any) -> List[Dict[str, Any]]:
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    return []


def _infer_winner(scoring: Dict[str, Any]) -> Optional[str]:
    """
    Try to determine a winner from scoring.
    Priority:
      1) scoring["best"]
      2) the option with rank == 1 in scoring["option_scores"]
      3) the option with highest total_score
    """
    best = scoring.get("best")
    if best:
        return best

    option_scores = scoring.get("option_scores") or []
    if not isinstance(option_scores, list) or not option_scores:
        return None

    # by rank
    try:
        top = min(option_scores, key=lambda x: x.get("rank", 1_000_000))
        if top.get("rank") == 1 and "option_id" in top:
            return top["option_id"]
    except Exception:
        pass

    # by total_score
    try:
        top2 = max(option_scores, key=lambda x: x.get("total_score", float("-inf")))
        return top2.get("option_id")
    except Exception:
        return None


def _auto_summary(*, winner: Optional[str], offers_count: int, confidence: float) -> str:
    if winner:
        return f"Recommended option: {winner}. Compared {offers_count} offers. Confidence ~ {confidence:.2f}."
    return f"No clear winner. Compared {offers_count} offers. Confidence ~ {confidence:.2f}."
