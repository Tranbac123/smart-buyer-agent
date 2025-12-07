from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from packages.control_plane.control_plane.core import ToolRegistry, ToolSpec
from packages.tools.tools.decision_tool import DecisionTool


class DecisionToolInput(BaseModel):
    options: List[Dict[str, Any]] = Field(default_factory=list)
    criteria: List[Dict[str, Any]] = Field(default_factory=list)
    prefs: Dict[str, Any] = Field(default_factory=dict)


class DecisionToolOutput(BaseModel):
    scoring: Dict[str, Any]
    explanation: Dict[str, Any]


_tool = DecisionTool()


async def decision_score_handler(
    options: List[Dict[str, Any]],
    criteria: List[Dict[str, Any]] | None = None,
    prefs: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload = {
        "options": options,
        "criteria": criteria or [],
        "prefs": prefs or {},
    }
    return await _tool.call(payload)  # type: ignore[arg-type]


def register_decision_tool(registry: ToolRegistry) -> None:
    spec = ToolSpec(
        name="decision_score",
        handler=decision_score_handler,
        description="Score candidate offers using weighted criteria.",
        input_schema=DecisionToolInput,
        output_schema=DecisionToolOutput,
        allowed_orgs=["org_demo", "org_premium"],
        tags=["decision", "scoring"],
    )
    registry.register(spec)

