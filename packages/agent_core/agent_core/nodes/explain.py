from __future__ import annotations

from typing import Dict, Any, List

from agent_core.agent_core.nodes.base import BaseNode
from packages.agent_core.agent_core.models import AgentState
from packages.tools.tools.registry import ToolRegistry


class ExplainNode(BaseNode):
    """
    Orchestrator node that ensures a clear, human-readable explanation
    exists after decision scoring.

    Responsibilities:
    - Normalize/complete explanation payload
    - Synthesize summary if missing
    - Derive best-by-criterion and trade-offs when absent
    - Keep pipeline resilient (fail-soft)
    """
    name = "explain"
    cost_per_call_tokens: int = 20  # optional budget charge per invocation

    def __init__(self, tools: ToolRegistry | None = None) -> None:
        # Tools are optional here; you could later plug an LLM-backed "explain" tool.
        self.tools = tools

    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        offers: List[Dict[str, Any]] = list((state.facts or {}).get("offers") or [])
        scoring: Dict[str, Any] = dict((state.facts or {}).get("scoring") or {})
        explanation: Dict[str, Any] = dict((state.facts or {}).get("explanation") or {})

        # Winner fallback (if DecisionNode didn't set it)
        winner = explanation.get("winner") or scoring.get("best") or _infer_winner_from_scores(scoring)
        explanation.setdefault("winner", winner)

        # Confidence fallback
        explanation.setdefault("confidence", float(scoring.get("confidence", 0.0)))
        # Best-by-criterion (derive if missing and data available)
        if not explanation.get("best_by_criterion"):
            explanation["best_by_criterion"] = _derive_best_by_criterion(scoring, offers)
        # Trade-offs (derive if missing and data available)
        if not explanation.get("trade_offs"):
            explanation["trade_offs"] = _derive_trade_offs(scoring, threshold=0.2)
        
        # Per-option bullets (very lightweight heuristics; keep short)
        if not explanation.get("bullets"):
            explanation["bullets"] = _derive_per_option_bullets(scoring, max_items=3)
        
        # Summary (ensure a concise, user-facing synthesis)
        if not explanation.get("summary"):
            explanation["summary"] = _compose_summary(
                winner=winner,
                offers_count=len(offers),
                confidence=float(explanation.get("confidence", 0.0)),
                tradeoffs=explanation.get("tradeoffs") or [],
                best_by_criterion=explanation.get("best_by_criterion") or {},
                max_len=320,
            )
        # Write back to state and return
        state.facts["explanation"] = explanation
        return state

# -------------------------------------------------------------------
# Helpers (pure functions) — intentionally framework/LLM-agnostic
# -------------------------------------------------------------------

def _infer_winner_from_scores(scoring: Dict[str, Any]) -> Optional[str]:
    option_scores = scoring.get("option_scores") or []
    if not isinstance(option_scores, list) or not option_scores:
        return None

    # Prefer rank==1 if present
    try:
        top_rank = min(option_scores, key=lambda x: x.get("rank", 1_000_000))
        if top_rank.get("rank") == 1 and "option_id" in top_rank:
            return top_rank["option_id"]
    except Exception:
        pass

    # Otherwise, pick highest total_score
    try:
        top_total = max(option_scores, key=lambda x: x.get("total_score", float("-inf")))
        return top_total.get("option_id")
    except Exception:
        return None


def _derive_best_by_criterion(scoring: Dict[str, Any], offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Scan per-option criterion_scores and pick the best normalized_value for each criterion.
    Expected shape per option (if available):
      option_scores[i]["criterion_scores"][<criterion_name>]["normalized_value"] -> float in [0, 1]
    """
    option_scores = scoring.get("option_scores") or []
    if not isinstance(option_scores, list) or not option_scores:
        return {}

    best: Dict[str, Dict[str, Any]] = {}
    for opt in option_scores:
        opt_id = opt.get("option_id")
        crit_scores = (opt.get("criterion_scores") or {}) if isinstance(opt.get("criterion_scores"), dict) else {}
        for crit, data in crit_scores.items():
            try:
                val = float(data.get("normalized_value", 0.0))
            except Exception:
                val = 0.0
            prev = best.get(crit)
            if prev is None or val > prev.get("value", -1.0):
                best[crit] = {"option_id": opt_id, "value": val}

    # Optionally attach a friendly title if we can match option_id back to offers
    id_to_title = {o.get("id") or o.get("sku") or o.get("url"): o.get("title") for o in offers}
    for crit, info in best.items():
        oid = info.get("option_id")
        if oid in id_to_title and id_to_title[oid]:
            info["title"] = id_to_title[oid]

    return best


def _derive_tradeoffs(scoring: Dict[str, Any], *, threshold: float = 0.2) -> List[Dict[str, Any]]:
    """
    Heuristic: for the top-2 (by total_score), report criteria where the
    normalized_value differs by at least `threshold`.
    """
    option_scores = scoring.get("option_scores") or []
    if not isinstance(option_scores, list) or len(option_scores) < 2:
        return []

    # Pick top-2 by total_score
    try:
        sorted_opts = sorted(option_scores, key=lambda x: x.get("total_score", float("-inf")), reverse=True)
    except Exception:
        return []

    a = sorted_opts[0]
    b = sorted_opts[1]
    crit_a = a.get("criterion_scores") or {}
    crit_b = b.get("criterion_scores") or {}
    tradeoffs: List[Dict[str, Any]] = []

    for crit in set(crit_a.keys()) | set(crit_b.keys()):
        try:
            va = float((crit_a.get(crit) or {}).get("normalized_value", 0.0))
            vb = float((crit_b.get(crit) or {}).get("normalized_value", 0.0))
        except Exception:
            continue
        diff = abs(va - vb)
        if diff >= threshold:
            better = a.get("option_id") if va > vb else b.get("option_id")
            tradeoffs.append({"criterion": crit, "better_option": better, "difference": round(diff, 3)})

    return tradeoffs


def _derive_per_option_bullets(scoring: Dict[str, Any], *, max_items: int = 3) -> List[Dict[str, Any]]:
    """
    Produce concise bullets for each option using criterion_scores.
    Example output item:
      {"option_id": "A", "pros": ["Strong battery", "Low price"], "cons": ["Heavier"], "note": "Rank #1"}
    """
    option_scores = scoring.get("option_scores") or []
    if not isinstance(option_scores, list) or not option_scores:
        return []

    out: List[Dict[str, Any]] = []
    for opt in option_scores:
        pros, cons = [], []
        rank = opt.get("rank")
        crit_scores = opt.get("criterion_scores") or {}
        for crit, data in crit_scores.items():
            try:
                v = float(data.get("normalized_value", 0.0))
            except Exception:
                v = 0.0
            raw = data.get("raw_value")
            if v >= 0.7:
                pros.append(f"Strong {crit}" + (f" ({raw})" if raw is not None else ""))
            elif v <= 0.3:
                cons.append(f"Weak {crit}" + (f" ({raw})" if raw is not None else ""))

        item = {"option_id": opt.get("option_id"), "pros": pros[:max_items], "cons": cons[:max_items]}
        if isinstance(rank, int):
            item["note"] = f"Rank #{rank}"
        out.append(item)

    return out


def _compose_summary(
    *,
    winner: Optional[str],
    offers_count: int,
    confidence: float,
    tradeoffs: List[Dict[str, Any]],
    best_by_criterion: Dict[str, Any],
    max_len: int = 320,
) -> str:
    """
    Build a compact, human-readable summary. Avoid long lists; keep it skimmable.
    """
    parts: List[str] = []
    if winner:
        parts.append(f"Recommended option: {winner}.")
    else:
        parts.append("No clear winner.")

    parts.append(f"Compared {offers_count} offers.")
    parts.append(f"Confidence ~ {confidence:.2f}.")

    # Add up to 2 notable trade-offs
    if tradeoffs:
        tops = tradeoffs[:2]
        tdesc = "; ".join(f"{t['criterion']}: {t['better_option']} better" for t in tops if "criterion" in t and "better_option" in t)
        if tdesc:
            parts.append(f"Notable trade-offs: {tdesc}.")

    # Add 1-2 best-by-criterion signals
    if best_by_criterion:
        tops = list(best_by_criterion.items())[:2]
        bdesc = "; ".join(f"Best {k}: {v.get('option_id')}" for k, v in tops if isinstance(v, dict) and v.get("option_id"))
        if bdesc:
            parts.append(bdesc + ".")

    summary = " ".join(parts)
    if len(summary) > max_len:
        summary = summary[: max_len - 1].rstrip() + "…"
    return summary