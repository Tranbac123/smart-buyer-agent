# quantumx-ai/apps/api/src/router/flows/smart_buyer_flow.py
from __future__ import annotations

import asyncio
import time
from typing import List, Optional, Dict, Any


from packages.agent_core.agent_core.models import AgentState
from packages.agent_core.agent_core.planner import build_initial_plan
from packages.search_core.search_core.ecommerce.price_compare import PriceCompareNode
from packages.tools.tools.registry import ToolRegistry
from packages.llm_client.llm_client.base import ILLMClient
from packages.memory_core.memory_core.base import IMemory
from packages.agent_core.agent_core.nodes.base import BaseNode
from packages.agent_core.agent_core.profiles.smart_buyer_profile import SmartBuyerProfile
from packages.agent_core.agent_core.nodes.explain import ExplainNode
from packages.agent_core.agent_core.nodes.decision import DecisionNode
from packages.agent_core.agent_core.nodes.finalize import FinalizeNode




class SmartBuyerFlow:
    name="smart_buyer"
    def __init__(
        self,
        *,
        tools: ToolRegistry,
        llm: ILLMClient,
        memory: Optional[IMemory] = None,
        profile: Optional[SmartBuyerProfile] = None,
        default_timeout_s: float = 20.0,
    ) -> None:
        self.tools = tools
        self.llm = llm
        self.memory = memory
        self.profile = profile or SmartBuyerProfile()
        self.default_timeout_s = default_timeout_s
        self.nodes: List[BaseNode] = []
        self._build = False
    
    async def build(self, state: AgentState) -> Dict[str, Any]:
        plan = await build_initial_plan(self.llm, self.profile, self.tools, self.memory, state)
        self.nodes = plan._instantiate_nodes(plan.steps)
        self._build = True
        return {"plan": plan.model_dump(mode="json")}
    
    async def run(self, state: AgentState, ctx: Dict[str, Any]) -> Dict[str, Any]:
        if not self._build:
            await self.build(state)
        timeout_s = float(ctx.get("timeout_s", self.default_timeout_s))
        return await asyncio.wait_for(self._run_nodes(state, ctx), timeout=timeout_s)
    
    async def _run_inner(self, state: AgentState, ctx: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.perf_counter()
        for idx, node in enumerate(self.nodes):
            if state.done:
                break
            state.step_idx = idx
            state = await node.run(state, ctx)
            if self._budget_exceeded(state):
                state.mark_done(
                    {
                        "offers": state.facts.get("offers", []),
                        "scoring": state.facts.get("scoring", {}),
                        "explanation": state.facts.get("explanation", {}),
                        "summary": "budget_exceeded",
                    }
                )
                break
        latency_ms = int((time.perf_counter() - t0) * 1000)
        out = state.output or {
            "offers": state.facts.get("offers", []),
            "scoring": state.facts.get("scoring", {}),
            "explanation": state.facts.get("explanation", {}),
        }
        if isinstance(out, dict):
            out.setdefault("metadata", {})
            out["metadata"]["latency_ms"] = latency_ms
        return out
    
    def _instantiate_nodes(self, steps: List[Any]) -> List[BaseNode]:
        nodes: List[BaseNode] = []
        for s in steps:
            k = getattr(s, "kind", None)
            tool = getattr(s, "tool", None)
            if k == "tool" and tool == "price_compare":
                nodes.append(PriceCompareNode(self.tools))
            elif k in ("decide",) or (k == "tool" and tool == "decision_score"):
                nodes.append(DecisionNode(self.tools))
            elif k in ("explain",):
                nodes.append(ExplainNode(self.tools))
            elif k in ("finalize",):
                nodes.append(FinalizeNode())
        if not nodes:
            nodes = [PriceCompareNode(self.tools), DecisionNode(self.tools), ExplainNode(self.tools), FinalizeNode()]
        if not isinstance(nodes[-1], FinalizeNode):
            nodes.append(FinalizeNode())
        return nodes

    def _budget_exceeded(self, state: AgentState) -> bool:
        if state.budget_tokens <= 0:
            return False
        return state.spent_tokens >= state.budget_tokens

