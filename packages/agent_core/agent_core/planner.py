from __future__ import annotations

import json
import re
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pydantic import BaseModel, Field, ValidationError, ConfigDict

from agent_core.agent_core.interfaces import ILLMClient, IMemory, IToolRegistry
from agent_core.agent_core.models import AgentState
from agent_core.agent_core.profiles.base_profile import BaseProfile

logger = logging.getLogger(__name__)

class PlanStepKind(str, Enum):
    THINK = "think"
    TOOL = "tool"
    RETRIEVE = "retrieve"
    DECIDE = "decide"
    EXPLAIN = "explain"
    FINALIZE = "finalize"


class PlanStepModel(BaseModel):
    kind: PlanStepKind
    name: Optional[str] = None
    tool: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    stop_if: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class PlanModel(BaseModel):
    steps: List[PlanStepModel]
    rationale: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class PlannerConfig(BaseModel):
    max_steps: int = 8
    enforce_allowed_tools: bool = True
    require_finalize: bool = True

class Planner:
    def __init__(
        self,
        llm: ILLMClient,
        profile: BaseProfile,
        tools: IToolRegistry,
        memory: Optional[IMemory] = None,
        config: Optional[ConfigDict] = None,
    ) -> None:
        self.llm = llm
        self.profile = profile
        self.tools = tools
        self.memory = memory
        self.config = config or PlannerConfig()

    async def plan(self, state: AgentState) -> PlanModel:
        sys, user = self._build_prompt(state)
        raw = await self._ask_llm(sys, user)
        plan = self._parse_or_fallback(raw, state)
        plan = self._post_validate(plan)
        return plan

    def _build_system_prompt(self) -> str:
        allow = ", ".join(self.profile.allowed_tools or [])
        return (
            "You are an agentic planner responsible for generating an execution plan. "
            "Return ONLY a single JSON object that strictly matches the provided schema. "
            "Do not add explanations, commentary, or any text outside the JSON object. "
            "Rules: "
            "keep the plan short and minimal; "
            "use only tools from allowed_tools; "
            "do not invent tool names; "
            "ensure steps form a logical sequence toward the user's goal; "
            "avoid redundant steps; "
            "the final step must be 'finalize'; "
            f"max_steps={self.config.max_steps}; "
            f"allowed_tools=[{allow}]. "
            "If uncertain, choose the simplest valid plan."
        )

    def _build_user_prompt(
        self,
        goal: str,
        facts: Dict[str, Any],
        memory: Dict[str, Any],
    ) -> str:
        schema_hint = (
            '{"steps":[{"kind":"think|tool|retrieve|decide|explain|finalize",'
            '"name?":"str","tool?":"str","params?":{},"stop_if?":"str"}],'
            '"rationale?":"str"}'
        )
        return (
            f"# Goal\n{goal}\n"
            f"# Context\n{json.dumps(facts, ensure_ascii=False)[:4000]}\n"
            f"# Memory\n{json.dumps(memory, ensure_ascii=False)[:2000]}\n"
            f"# Constraints\nmax_steps={self.config.max_steps}\n"
            f"# Output JSON schema (conceptual)\n{schema_hint}"
        )
    
    def _build_prompt(self, state: AgentState) -> Tuple[str, str]:
        facts = state.facts or {}
        mem = self._read_memory_snapshot(state)
        goal = state.query.strip()
        sys = self._build_system_prompt()
        user = self._build_user_prompt(goal=goal, facts=facts, memory=mem)
        return sys, user

    async def _ask_llm(self, sys: str, user: str) -> str:
        try:
            rsp = await self.llm.complete(system=sys, user=user, format="json")
            if isinstance(rsp, str):
                return rsp
            if hasattr(rsp, "text"):
                return rsp.text # type: ignore[no-any-return]
            if hasattr(rsp, "content"):
                return rsp.content # type: ignore[no-any-return]
            return str(rsp)
        except Exception as e:
            logger.warning(f"Failed to ask LLM: {e}")
            return json.dumps({"error": type(e).__name__, "fallback": True})

    def _parse_or_fallback(self, raw: str, state: AgentState) -> PlanModel:
        obj = self._extract_json(raw)
        if obj is not None:
            try:
                plan = PlanModel.model_validate(obj)
                return self._trim_and_filter(plan)
            except ValidationError as e:
                logger.warning("Planner plan validation error: %s", e, exc_info=True)
        logger.info(
            "Planner using fallback plan for flow=%s session_id=%s",
            getattr(self.profile, "flow", None),
            getattr(state, "session_id", None),
        )
        return self._fallback_plan(state)
        
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        s = text.strip()
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        if s.startswith("```"):
            s2 = re.sub(r"^```[a-zA-Z]*\n?", "", s)
            s2 = s2.rstrip("`").strip()
            try:
                obj = json.loads(s2)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

        m = re.search(r"\{[\s\S]*\}\s*$", s)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
        return None

    def _trim_and_filter(self, plan: PlanModel) -> PlanModel:
        steps = plan.steps[: self.config.max_steps]
        if self.config.enforce_allowed_tools and self.profile.allowed_tools:
            allowed = set(self.profile.allowed_tools)
            filtered: List[PlanStepModel] = []
            for s in steps:
                if s.kind == PlanStepKind.TOOL:
                    if not s.tool:
                        continue
                    if s.tool not in allowed:
                        continue
                    if hasattr(self.tools, "has_tool"):
                        try:
                            if not self.tools.has_tool(s.tool):  # type: ignore[attr-defined]
                                continue
                        except Exception:
                            logger.debug("Planner tool registry has_tool failed for %s", s.tool)
                    filtered.append(s)
                else:
                    filtered.append(s)
            steps = filtered
        return PlanModel(steps=steps, rationale=plan.rationale)

    def _post_validate(self, plan: PlanModel) -> PlanModel:
        if self.config.require_finalize:
            if not plan.steps or plan.steps[-1].kind != PlanStepKind.FINALIZE:
                plan.steps.append(PlanStepModel(kind=PlanStepKind.FINALIZE, name="finalize"))
        if not plan.steps:
            plan.steps = [PlanStepModel(kind=PlanStepKind.FINALIZE, name="finalize")]
        return plan

    def _read_memory_snapshot(self, state: AgentState) -> Dict[str, Any]:
        if not self.memory:
            return {}
        try:
            snap = self.memory.snapshot(session_id=state.session_id)  # type: ignore[attr-defined]
            return snap or {}
        except Exception as e:
            logger.debug("Planner memory snapshot failed: %s", e, exc_info=True)
            return {}

    def _fallback_plan(self, state: AgentState) -> PlanModel:
        flow = getattr(self.profile, "flow", None) or "chat"
        if flow == "smart_buyer":
            steps = [
                PlanStepModel(kind=PlanStepKind.THINK, name="understand"),
                PlanStepModel(
                    kind=PlanStepKind.TOOL,
                    name="price_compare",
                    tool="price_compare",
                    params={"top_k": 6},
                ),
                PlanStepModel(
                    kind=PlanStepKind.TOOL,
                    name="scraper_fetch",
                    tool="scraper_fetch",
                    params={},
                ),
                PlanStepModel(
                    kind=PlanStepKind.DECIDE,
                    name="score",
                    tool="decision_score",
                    params={},
                ),
                PlanStepModel(kind=PlanStepKind.EXPLAIN, name="explain"),
                PlanStepModel(kind=PlanStepKind.FINALIZE, name="finalize"),
            ]
            return PlanModel(steps=steps, rationale="fallback: smart_buyer default")
        if flow == "deep_research":
            steps = [
                PlanStepModel(kind=PlanStepKind.RETRIEVE, name="retrieve"),
                PlanStepModel(kind=PlanStepKind.THINK, name="synthesize"),
                PlanStepModel(kind=PlanStepKind.EXPLAIN, name="explain"),
                PlanStepModel(kind=PlanStepKind.FINALIZE, name="finalize"),
            ]
            return PlanModel(steps=steps, rationale="fallback: deep_research default")
        steps = [
            PlanStepModel(kind=PlanStepKind.THINK, name="draft"),
            PlanStepModel(kind=PlanStepKind.FINALIZE, name="finalize"),
        ]
        return PlanModel(steps=steps, rationale="fallback: chat default")
        
async def build_initial_plan(
    llm = ILLMClient,
    profile = BaseProfile,
    tools = IToolRegistry,
    memory = Optional[IMemory],
    state = AgentState,
    cfg: Optional[PlannerConfig] = None,
) -> PlanModel:
    planner = Planner(llm=llm, profile=profile, tools=tools, memory=memory, config=cfg)
    return await planner.plan(state)
