# packages/tools/tools/decision_tool.py
from __future__ import annotations

"""
DecisionTool
------------
Scores candidate options against user (or default) criteria, applies optional
dominance (Pareto) filtering, and returns both a normalized scoring bundle and
a human-readable explanation.

Contract (via ToolRegistry):
  input : {
    "options": list[dict],           # normalized offers/options
    "criteria": list[dict] | None,   # [{"name", "weight", "maximize", ...}]
    "prefs": dict | None             # optional preferences (unused here but forwarded to explainer)
  }
  output: {
    "scoring": {
      "confidence": float,           # ~[0..1], heuristic based on top1 vs top2 margin
      "option_scores": list[dict],   # normalized shape for downstream nodes
      "best": str | None             # best option_id if resolvable
    },
    "explanation": dict              # pros/cons, trade-offs, summary
  }

Notes:
- We intentionally keep this tool *LLM-free* so it is cheap and deterministic.
- The concrete scoring logic lives in decision_core.scoring; this tool orchestrates and normalizes.
"""
from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging
import math

from packages.decision_core.decision_core.scoring import Scoring, Criterion
from packages.decision_core.decision_core.explainer import Explainer

logger = logging.getLogger("quantumx.tools.decision")


class DecisionTool:
    """
    Production-friendly decision tool with optional Pareto filtering and
    robust output normalization.

    Parameters
    ----------
    enable_pareto : bool
        If True, prune strictly dominated options before scoring.
    """
    def __init__(self, *, enable_pareto: bool = True) -> None:
        self.enable_pareto = enable_pareto
        self.scorer = Scoring() # criteria will be injected per-call
        self.explainer = Explainer() # optionally can be given an LLM client later
    
    async def call(self, playload: Dict[str, Any]) -> Dict[str, Any]:
        # -------- Parse & validate input --------
        options: List[Dict[str, Any]] = _as_list_of_dicts(payload.get("options"))
        if not options:
            return _empty_result(summary="No options provided")
        raw_criteria = payload.get("criteria")
        criteria: List[Criterion] = _parse_criteria(raw_criteria)

        # If caller didn't pass criteria, respect whatever is already on scorer; otherwise set
        if criteria:
            self.scorer.criteria = criteria
        # -------- Optional: Pareto prune before scoring (if enough attributes) --------
        candidates = options
        if self.enable_pareto and len(options) >= 3 and len(self.scorer.criteria) >= 2:
            try:
                keep_idx = _pareto_filter(options, self.scorer.criteria)
                candidates = [options[i] for i in keep_idx]
                if 0 < len(keep_idx) < len(options):
                    logger.debug("DecisionTool: pareto pruned %d/%d options", len(options) - len(keep_idx), len(options))
            except Exception as e:
                logger.debug("DecisionTool: pareto filtering skipped due to error: %s", e)
        # -------- Score & rank --------
        try:
            scored_list = self.scorer.score_options(candidates, normalize=True)
        except Exception as e:
            logger.exception("DecisionTool: scoring failed: %s", e)
            return _empty_result(summary=f"scoring error: {type(e).__name__}")

        if not scored_list:
            return _empty_result(summary="no scored results")
        
        # -------- Normalize scoring bundle --------
        option_scores, best_id = _normalize_option_scores(scored_list)
        confidence = _confidence_from_margin(option_scores)

        scoring_bundle = {
            "confidence": confidence,
            "option_scores": option_scores,
            "best": best_id,
        }
        # -------- Explanation (pros/cons, trade-offs, summary) --------
        try:
            explanation = self.explainer.compare_options(candidates, scored_list)
            # Ensure a winner & a concise fallback summary if missing
            explanation = _fix_explanation(explanation, best_id, confidence, len(candidates))
        except Exception as e:
            logger.debug("DecisionTool: explanation fallback due to error: %s", e)
            explanation = _fallback_explanation(best_id, confidence, len(candidates), note="explain-error")

        return {
            "scoring": scoring_bundle,
            "explanation": explanation,
        }

# =============================================================================
# Helpers (pure/robust)
# =============================================================================

def _as_list_of_dicts(v: Any) -> List[Dict[str, Any]]:
    if not isinstance(v, list):
        return []
    return [x for x in v if isinstance(x, dict)]

def _empty_result(summary: str = "no options") -> Dict[str, Any]:
    return {
        "scoring": {
            "confidence": 0.0,
            "option_scores": [],
            "best": None,
        },
        "explanation": {
            "winner": None,
            "confidence": 0.0,
            "best_by_criterion": {},
            "tradeoffs": [],
            "per_option": [],
            "summary": summary,
        },
    }

def _parse_criteria(v: Any) -> List[Criterion]:
    if v is None:
        return []
    items: List[Dict[str, Any]] = []
    if isinstance(v, dict):
        items = [v]
    elif isinstance(v, (list, tuple)):
        items = [x for x in v if isinstance(x, dict)]
    else:
        return []

    out: List[Criterion] = []
    for c in items:
        try:
            out.append(
                Criterion(
                    name=str(c.get("name", "score")),
                    weight=float(c.get("weight", 0.0)),
                    maximize=bool(c.get("maximize", True)),
                    description=str(c.get("description", "")) if c.get("description") is not None else None,
                )
            )
        except Exception as e:
            logger.debug("DecisionTool: drop invalid criterion %s (%s)", c, e)
    return out


def _extract_option_id(opt: Dict[str, Any]) -> Optional[str]:
    # try common keys in order of specificity
    for k in ("id", "sku", "offer_id", "url", "title"):
        v = opt.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _normalize_option_scores(scored_list: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Convert scorer output into a stable shape for downstream nodes:
      - Ensure ranks are consecutive starting at 1
      - Attach a resolvable option_id
      - Keep criterion_scores structure if present
    Returns (option_scores, best_id)
    """
    # Sort by total_score descending (should already be)
    scored_sorted = sorted(scored_list, key=lambda x: x.get("total_score", float("-inf")), reverse=True)

    option_scores: List[Dict[str, Any]] = []
    best_id: Optional[str] = None

    for i, s in enumerate(scored_sorted, start=1):
        opt = s.get("option", {}) if isinstance(s.get("option"), dict) else {}
        oid = _extract_option_id(opt)
        if i == 1:
            best_id = oid

        entry = {
            "option_id": oid,
            "rank": i,
            "total_score": float(s.get("total_score", 0.0)),
            "criterion_scores": s.get("criterion_scores") or {},
        }
        option_scores.append(entry)

    return option_scores, best_id


def _confidence_from_margin(option_scores: List[Dict[str, Any]]) -> float:
    """
    Heuristic confidence based on the margin between top1 and top2.
    Maps margin -> [~0.55 .. 0.95]. Returns 0.6 if only one option.
    """
    if not option_scores:
        return 0.0
    if len(option_scores) == 1:
        return 0.6

    s1 = float(option_scores[0].get("total_score", 0.0))
    s2 = float(option_scores[1].get("total_score", 0.0))
    margin = max(0.0, s1 - s2)

    # Smooth mapping via tanh; scale margin a bit to spread 0..1
    raw = 0.5 + 0.45 * math.tanh(margin * 2.0)
    return max(0.0, min(0.99, raw))


def _fix_explanation(
    explanation: Dict[str, Any],
    best_id: Optional[str],
    confidence: float,
    offers_count: int,
) -> Dict[str, Any]:
    if not isinstance(explanation, dict):
        return _fallback_explanation(best_id, confidence, offers_count, note="invalid-explanation")

    explanation.setdefault("winner", best_id)
    explanation.setdefault("confidence", confidence)
    explanation.setdefault("best_by_criterion", {})
    explanation.setdefault("tradeoffs", [])
    explanation.setdefault("per_option", [])

    if not explanation.get("summary"):
        explanation["summary"] = _compose_summary(best_id, offers_count, confidence)

    return explanation


def _compose_summary(best_id: Optional[str], offers_count: int, confidence: float) -> str:
    if best_id:
        return f"Recommended: {best_id}. Compared {offers_count} options. Confidence ~ {confidence:.2f}."
    return f"No clear winner. Compared {offers_count} options. Confidence ~ {confidence:.2f}."


def _fallback_explanation(best_id: Optional[str], confidence: float, offers_count: int, *, note: str) -> Dict[str, Any]:
    return {
        "winner": best_id,
        "confidence": confidence,
        "best_by_criterion": {},
        "tradeoffs": [],
        "per_option": [],
        "summary": _compose_summary(best_id, offers_count, confidence) + f" ({note})",
    }


# ---------------- Pareto (dominance) filtering ----------------

def _pareto_filter(options: List[Dict[str, Any]], criteria: List[Criterion]) -> List[int]:
    """
    Return indices of non-dominated options w.r.t. provided criteria.
    - For maximize=True, higher is better; for maximize=False, lower is better.
    - Missing criterion values are treated as neutral (not dominating).
    Complexity: O(n^2 * m). Fine for dozens of options.
    """
    n = len(options)
    m = len(criteria)
    if n <= 2 or m == 0:
        return list(range(n))

    # Extract matrix of values per criterion
    vals: List[List[Optional[float]]] = []
    for opt in options:
        row: List[Optional[float]] = []
        for c in criteria:
            v = opt.get(c.name)
            try:
                row.append(float(v))
            except Exception:
                row.append(None)  # missing/invalid
        vals.append(row)

    def dominates(i: int, j: int) -> bool:
        """Return True if option i dominates option j."""
        better_or_equal_all = True
        strictly_better_once = False
        for k, c in enumerate(criteria):
            vi = vals[i][k]
            vj = vals[j][k]
            if vi is None or vj is None:
                # Unknown -> cannot use to claim dominance on this criterion
                continue
            if c.maximize:
                if vi < vj:
                    better_or_equal_all = False
                    break
                if vi > vj:
                    strictly_better_once = True
            else:
                if vi > vj:
                    better_or_equal_all = False
                    break
                if vi < vj:
                    strictly_better_once = True
        return better_or_equal_all and strictly_better_once

    keep = [True] * n
    for i in range(n):
        if not keep[i]:
            continue
        for j in range(n):
            if i == j or not keep[j]:
                continue
            if dominates(i, j):
                keep[j] = False

    return [idx for idx, k in enumerate(keep) if k]