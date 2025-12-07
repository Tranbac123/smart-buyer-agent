from __future__ import annotations

from typing import Any, Dict, Optional

from packages.agent_core.agent_core.models import AgentState
from packages.control_plane.control_plane.core import RequestContext


def build_request_context(
    state: AgentState,
    overrides: Optional[Dict[str, Any]] = None,
) -> RequestContext:
    """
    Build a RequestContext from AgentState metadata, with optional overrides.
    """
    overrides = overrides or {}
    meta = state.metadata or {}

    def _pick(key: str, default: Any = None) -> Any:
        return overrides.get(key) or meta.get(key) or default

    request_id = _pick("request_id", state.session_id)
    user_id = _pick("user_id", "user_demo")
    org_id = _pick("org_id", "org_demo")
    flow_name = _pick("flow_name", "smart_buyer")
    role = _pick("role", "user")
    channel = _pick("channel", "http")

    metadata = {
        "role": role,
        "channel": channel,
    }

    for key, value in overrides.items():
        if key not in {"request_id", "user_id", "org_id", "flow_name", "role", "channel"}:
            metadata[key] = value

    return RequestContext(
        request_id=request_id,
        user_id=user_id,
        org_id=org_id,
        flow_name=flow_name,
        session_id=state.session_id,
        metadata=metadata,
    )


def halt_state_with_error(
    state: AgentState,
    *,
    reason: str,
    message: Optional[str],
    tool: Optional[str],
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Halt the agent state with a standardized error payload so the HTTP layer
    can translate it into the correct status code.
    """
    extra_metadata = extra_metadata or {}
    state.metadata["halt_reason"] = reason
    if message:
        state.metadata["halt_message"] = message

    metadata = {
        "error": reason,
        "message": message,
        "tool": tool,
        **extra_metadata,
    }

    payload = {
        "offers": state.facts.get("offers", []),
        "scoring": state.facts.get(
            "scoring",
            {"confidence": 0.0, "option_scores": [], "best": None},
        ),
        "explanation": state.facts.get(
            "explanation",
            {"summary": message or reason, "tradeoffs": [], "best_by_criterion": {}, "per_option": []},
        ),
        "metadata": metadata,
    }
    state.halt(reason, output=payload)


