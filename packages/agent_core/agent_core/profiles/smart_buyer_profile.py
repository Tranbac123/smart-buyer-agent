# packages/agent_core/agent_core/profiles/smart_buyer_profile.py
from __future__ import annotations

"""
SmartBuyerProfile
-----------------
A compact, production-ready profile for the Smart-Buyer flow.

Responsibilities:
- Define allowed tools and soft resource limits (tokens/steps).
- Provide sensible default MCDM criteria when the user does not supply any.
- Lightly adapt criteria based on user preferences (e.g., budget, tags).
- Keep it framework-agnostic and easy to test.

Usage:
    profile = SmartBuyerProfile()
    criteria = profile.make_criteria(prefs={"budget": 8_000_000, "required_tags": ["fast", "authentic"]})
    allowed = profile.is_tool_allowed("price_compare")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


# ---- Typed contracts kept minimal (no dependency on decision_core) ----

class CriterionTD(TypedDict, total=False):
    name: str
    weight: float       # expected in [0..1] after normalization
    maximize: bool      # True = higher is better
    description: Optional[str]


# ---- Constants & lightweight heuristics ----

# Terms that hint the user cares about shipping speed
_FAST_TAGS = {"fast", "express", "same-day", "same day", "overnight", "instant"}

# Terms that hint the user cares about seller authenticity/reputation
_TRUST_TAGS = {"authentic", "genuine", "official", "flagship", "verified"}

# Safe numeric bounds
_EPS = 1e-12
_W_MIN = 0.0
_W_MAX = 1.0


@dataclass(slots=True)
class SmartBuyerProfile:
    """
    Profile controlling constraints and defaults for the Smart-Buyer flow.
    Keep fields stable; add behavior via methods instead of exposing internals.
    """

    # Which tools the flow is allowed to call
    allow_tools: List[str] = field(default_factory=lambda: ["price_compare", "decision_score"])

    # Soft resource limits
    budget_tokens: int = 12_000
    max_steps: int = 6

    # Default, domain-oriented criteria (weights will be normalized)
    default_criteria: List[CriterionTD] = field(
        default_factory=lambda: [
            {"name": "price",           "weight": 0.50, "maximize": False, "description": "Lower is better"},
            {"name": "seller_rating",   "weight": 0.20, "maximize": True,  "description": "Higher is better"},
            {"name": "shipping_speed",  "weight": 0.15, "maximize": True,  "description": "Faster is better"},
            {"name": "warranty",        "weight": 0.10, "maximize": True,  "description": "Longer/Better coverage"},
            {"name": "return_policy",   "weight": 0.05, "maximize": True,  "description": "Easier returns"},
        ]
    )

    # ---- Public API ---------------------------------------------------------

    def make_criteria(self, prefs: Optional[Dict[str, Any]] = None) -> List[CriterionTD]:
        """
        Build a criteria list, optionally adapted by user preferences.
        Returns a *new* list; the internal default_criteria is not mutated.

        Heuristics (deliberately conservative):
          - If `prefs.budget` is present => gently up-weight `price`.
          - If tags contain fast-related terms => up-weight `shipping_speed`.
          - If tags contain authenticity terms => up-weight `seller_rating`.
          - Always renormalize weights to sum ~ 1.0.
        """
        prefs = prefs or {}
        criteria = [c.copy() for c in self.default_criteria]

        # 1) Budget nudges focus on price
        if _get_float(prefs.get("budget")) is not None:
            _bump_weight(criteria, name="price", by=0.06)

        # 2) Tags → adapt shipping/seller trust
        tags = _normalize_tags(prefs.get("required_tags"))
        if tags:
            if tags & _FAST_TAGS:
                _bump_weight(criteria, name="shipping_speed", by=0.04)
            if tags & _TRUST_TAGS:
                _bump_weight(criteria, name="seller_rating", by=0.03)

        # 3) Final normalization
        _clamp_weights(criteria)
        _normalize_weights(criteria)
        return criteria

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check whether a tool is allowed for this profile."""
        return tool_name in self.allow_tools

    def apply_limits(self, *, budget_tokens: Optional[int] = None, max_steps: Optional[int] = None) -> None:
        """Adjust soft limits at runtime (e.g., per-tenant or A/B)."""
        if isinstance(budget_tokens, int) and budget_tokens > 0:
            self.budget_tokens = budget_tokens
        if isinstance(max_steps, int) and max_steps > 0:
            self.max_steps = max_steps

    def to_dict(self) -> Dict[str, Any]:
        """Serialize key profile information for debugging/telemetry."""
        return {
            "allow_tools": list(self.allow_tools),
            "budget_tokens": int(self.budget_tokens),
            "max_steps": int(self.max_steps),
            "default_criteria": [c.copy() for c in self.default_criteria],
        }


# ---- Internal helpers (pure functions) ---------------------------------------

def _get_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _normalize_tags(v: Any) -> set[str]:
    if v is None:
        return set()
    if isinstance(v, str):
        items = [v]
    elif isinstance(v, (list, tuple, set)):
        items = list(v)
    else:
        return set()
    return {str(x).strip().lower() for x in items if str(x).strip()}


def _bump_weight(criteria: List[CriterionTD], *, name: str, by: float) -> None:
    """
    Increase the weight of the named criterion by `by` (small positive value).
    To keep the overall mass stable, subtract the same `by` from the others
    proportionally to their current weights.
    """
    if by <= 0:
        return

    target = None
    for c in criteria:
        if c.get("name") == name:
            target = c
            break
    if target is None:
        return

    target_w = float(target.get("weight", 0.0))
    target["weight"] = target_w + by

    # Subtract from others proportionally
    others = [c for c in criteria if c is not target]
    total_others = sum(float(c.get("weight", 0.0)) for c in others)
    if total_others <= _EPS:
        return
    for c in others:
        w = float(c.get("weight", 0.0))
        c["weight"] = max(_W_MIN, w - by * (w / total_others))


def _clamp_weights(criteria: List[CriterionTD]) -> None:
    """Clamp all weights to [0..1] to prevent drift from successive bumps."""
    for c in criteria:
        w = float(c.get("weight", 0.0))
        c["weight"] = min(_W_MAX, max(_W_MIN, w))


def _normalize_weights(criteria: List[CriterionTD]) -> None:
    """
    Normalize weights to sum exactly 1.0.
    If all zeros, assign uniform weights.
    """
    total = sum(float(c.get("weight", 0.0)) for c in criteria)
    if total <= _EPS:
        n = max(1, len(criteria))
        w = 1.0 / n
        for c in criteria:
            c["weight"] = w
        return

    inv_total = 1.0 / total
    for c in criteria:
        c["weight"] = float(c.get("weight", 0.0)) * inv_total
