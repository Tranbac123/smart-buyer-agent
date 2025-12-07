# quantumx-ai/apps/api/src/router/flows/smart_buyer_flow.py
from __future__ import annotations

import asyncio
import time
from typing import List, Optional, Dict, Any


from packages.agent_core.agent_core.models import AgentState
from packages.agent_core.agent_core.planner import build_initial_plan
from packages.agent_core.agent_core.nodes.price_compare_node import PriceCompareNode
from packages.control_plane.control_plane.tool_registry import ToolRegistry
from packages.llm_client.llm_client.base import ILLMClient
from packages.memory_core.memory_core.base import IMemory
from packages.agent_core.agent_core.nodes.base import BaseNode
from packages.agent_core.agent_core.profiles.smart_buyer_profile import SmartBuyerProfile
from packages.agent_core.agent_core.nodes.explain import ExplainNode
from packages.agent_core.agent_core.nodes.decision import DecisionNode
from packages.agent_core.agent_core.nodes.finalize import FinalizeNode
from packages.agent_core.agent_core.nodes.scraper_node import ScraperNode
from packages.control_plane.control_plane.core import ControlPlane


class SmartBuyerFlow:
    name="smart_buyer"
    def __init__(
        self,
        *,
        tools: ToolRegistry,
        llm: ILLMClient,
        memory: Optional[IMemory] = None,
        profile: Optional[SmartBuyerProfile] = None,
        control_plane: Optional[ControlPlane] = None,
        default_timeout_s: float = 20.0,
        default_max_steps: Optional[int] = None,
    ) -> None:
        self.tools = tools
        self.llm = llm
        self.memory = memory
        self.profile = profile or SmartBuyerProfile()
        self.control_plane = control_plane
        self.default_timeout_s = default_timeout_s
        self.default_max_steps = default_max_steps or self.profile.max_steps
        self.nodes: List[BaseNode] = []
        self._build = False
    
    async def build(self, state: AgentState) -> Dict[str, Any]:
        plan = await build_initial_plan(self.llm, self.profile, self.tools, self.memory, state)
        self.nodes = self._instantiate_nodes(plan.steps)
        self._build = True
        return {"plan": plan.model_dump(mode="json")}
    
    async def run(self, state: AgentState, ctx: Dict[str, Any]) -> Dict[str, Any]:
        if not self._build:
            await self.build(state)
        timeout_s = float(ctx.get("timeout_s", self.default_timeout_s))
        return await asyncio.wait_for(self._run_inner(state, ctx), timeout=timeout_s)
    
    async def _run_inner(self, state: AgentState, ctx: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.perf_counter()
        max_steps = self.default_max_steps or 0
        for node in self.nodes:
            if state.done or state.halted:
                break
            if max_steps and state.step_index >= max_steps:
                state.halt(
                    "max_steps_exceeded",
                    output={
                        "offers": state.facts.get("offers", []),
                        "scoring": state.facts.get("scoring", {}),
                        "explanation": state.facts.get("explanation", {}),
                        "summary": "max_steps_exceeded",
                    },
                )
                break
            state.next_step(node.name)
            state = await node.run(state, ctx)
            if self._budget_exceeded(state):
                state.halt("token_budget_exceeded", output={
                    "offers": state.facts.get("offers", []),
                    "scoring": state.facts.get("scoring", {}),
                    "explanation": state.facts.get("explanation", {}),
                    "summary": "budget_exceeded",
                })
                break
        latency_ms = int((time.perf_counter() - t0) * 1000)
        out = state.output or {
            "offers": state.facts.get("offers", []),
            "scoring": state.facts.get("scoring", {}),
            "explanation": state.facts.get("explanation", {}),
        }
        if isinstance(out, dict):
            metadata = out.setdefault("metadata", {})
            metadata.setdefault("latency_ms", latency_ms)
            metadata.setdefault("step_index", state.step_index)
            if state.halted:
                metadata.setdefault("halted", True)
            out["metadata"] = {**state.metadata, **metadata}
        return out
    
    def _instantiate_nodes(self, steps: List[Any]) -> List[BaseNode]:
        nodes: List[BaseNode] = []
        for s in steps:
            k = getattr(s, "kind", None)
            tool = getattr(s, "tool", None)
            if k == "tool" and tool == "price_compare":
                nodes.append(
                    PriceCompareNode(
                        tools=self.tools,
                        control_plane=self.control_plane,
                    )
                )
            elif k == "tool" and tool == "scraper_fetch":
                nodes.append(
                    ScraperNode(
                        tools=self.tools,
                        control_plane=self.control_plane,
                    )
                )
            elif k in ("decide",) or (k == "tool" and tool == "decision_score"):
                nodes.append(
                    DecisionNode(
                        self.tools,
                        control_plane=self.control_plane,
                    )
                )
            elif k in ("explain",):
                nodes.append(ExplainNode(self.tools))
            elif k in ("finalize",):
                nodes.append(FinalizeNode())
        if not nodes:
            nodes = [
                PriceCompareNode(self.tools, control_plane=self.control_plane),
                ScraperNode(self.tools, control_plane=self.control_plane),
                DecisionNode(self.tools, control_plane=self.control_plane),
                ExplainNode(self.tools),
                FinalizeNode(),
            ]
        if not isinstance(nodes[-1], FinalizeNode):
            nodes.append(FinalizeNode())
        return nodes

    def _budget_exceeded(self, state: AgentState) -> bool:
        budget = getattr(state, "budget_token", 0)
        spent = getattr(state, "spent_token", 0)
        if budget <= 0:
            return False
        return spent >= budget

