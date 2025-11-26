from __future__ import annotations

from typing import Dict, Any, List, Optional

from agent_core.agent_core.nodes.base import BaseNode
from packages.agent_core.agent_core.models import AgentState
from packages.tools.tools.registry import ToolRegistry

class DecisionNode(BaseNode):
    """
    Orchestrator node that scores options and produces an explanation.

    Responsibilities:
    - Read offers from AgentState.facts["offers"]
    - Normalize/forward criteria to the decision tool
    - Call ToolRegistry("decision_score")
    - Write "scoring" and "explanation" back to AgentState.facts
    - Fail-soft with sensible defaults when no offers/criteria
    """
    name = "decision"
    cost_per_call_tokens: int = 80 # optional: charge some tokens per call

    def __init__(self, tools: ToolRegistry, *, tool_name: str = "decision_score") -> None:
        self.tools = tools
        self.tool_name = tool_name
    
    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        offers: List[Dict[str, Any]] = list((state.facts or {}).get("offers") or [])
        if not offers:
            # No offers to score → keep pipeline alive with empty results
            state.facts["scoring"] = _default_scoring()
            state.facts["explanation"] = _default_explanation(summary="no offers to score")
            return state
        # Criteria can come from state (preferred) or ctx
        criteria_in = (state.facts or {}).get("criteria") or ctx.get("criteria")
        criteria = _normalize_criteria(criteria_in)

        # Optional preferences (may be used by your tool/scorer)
        prefs: Dict[str, Any] = dict((state.facts or {}).get("prefs") or {})
        payload: Dict[str, Any] = {"options": offers, "criteria": criteria, "prefs": prefs}

        # ---- Tool call ----
        # Expected tool contract (MVP):
        #   input : {"options": [...], "criteria": [...], "prefs": {...}}
        #   output: {"scoring": {...}, "explanation": {...}}
        res = await self.tools.call(self.tool_name, payload)
        scoring: Dict[str, Any] = dict(res.get("scoring") or _default_scoring())
        explanation: Dict[str, Any] = dict(
            res.get("explanation") or _default_explanation(confidence=scoring.get("confidence", 0.0))
        )

        # Ensure a winner if missing (best rank == 1 or highest total_score)
        if explanation.get("winner") is None:
            explanation["winner"] = _infer_winner(scoring)
        
        # Ensure a summary if missing
        explanation.setdefault("summary", _auto_summary(explanation, offers_count=len(offers)))

        # Write back to state
        state.facts["scoring"] = scoring
        state.facts["explanation"] = explanation
        return state

# Helpers
def _default_scoring() -> Dict[str, Any]:
    return {"confidence": 0.0, "option_scores": [], "best": None}


def _default_explanation(
    *,
    summary: str = "",
    confidence: float = 0.0,
) -> Dict[str, Any]:
    return {
        "winner": None,
        "confidence": confidence,
        "best_by_criterion": {},
        "tradeoffs": [],
        "per_option": [],
        "summary": summary,
    }


def _normalize_criteria(v: Any) -> List[Dict[str, Any]]:
    """
    Accepts:
      - None
      - list[dict] already normalized
      - dict-like single criterion
    Returns a list[dict] with minimal shape: {"name": str, "weight": float, "maximize": bool, ...}
    """
    if v is None:
        return []
    if isinstance(v, dict):
        return [_coerce_criterion(v)]
    if isinstance(v, (list, tuple)):
        return [_coerce_criterion(x) for x in v if isinstance(x, (dict,))]
    # Unknown format → ignore to avoid hard failures
    return []


def _coerce_criterion(c: Dict[str, Any]) -> Dict[str, Any]:
    name = str(c.get("name", "")).strip() or "score"
    try:
        weight = float(c.get("weight", 0.0))
    except Exception:
        weight = 0.0
    maximize = bool(c.get("maximize", True))
    out = {"name": name, "weight": weight, "maximize": maximize}
    # Keep any extra fields (e.g., bounds, description) if provided
    for k, v in c.items():
        if k not in out:
            out[k] = v
    return out


def _infer_winner(scoring: Dict[str, Any]) -> Optional[str]:
    """
    Try to determine winner from scoring payload.
    Priority:
      1) scoring["best"]
      2) option with rank == 1 in scoring["option_scores"]
      3) option with highest total_score
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


def _auto_summary(explanation: Dict[str, Any], *, offers_count: int) -> str:
    winner = explanation.get("winner")
    conf = explanation.get("confidence", 0.0)
    if winner:
        return f"Recommended option: {winner}. Consider {offers_count} offers. Confidence ~ {conf:.2f}."
    return f"No clear winner. Consider {offers_count} offers. Confidence ~ {conf:.2f}."
