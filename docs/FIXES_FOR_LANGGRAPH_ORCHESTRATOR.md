# Fixes for LangGraph-Style Orchestrator

## Critical Issues to Fix

### Issue 1: Field Name Consistency
**Problem**: Models use singular, but code uses plural

**Files to update**:
1. `packages/agent_core/agent_core/models.py`
2. `packages/agent_core/agent_core/nodes/base.py`
3. `apps/api/src/router/flows/smart_buyer_flow.py`

---

### Issue 2: Method Name Mismatch
**Problem**: `run()` calls `_run_nodes()` but method is named `_run_inner()`

**File**: `apps/api/src/router/flows/smart_buyer_flow.py`

---

### Issue 3: Python Syntax Error
**Problem**: `list[str](...)` is invalid syntax

**File**: `packages/agent_core/agent_core/nodes/base.py`

---

### Issue 4: Wrong Method Called
**Problem**: `self.spent_tokens()` doesn't exist, should be `self.spend_tokens()`

**File**: `packages/agent_core/agent_core/nodes/base.py`

---

### Issue 5: Method Called on Wrong Object
**Problem**: `plan._instantiate_nodes()` but PlanModel doesn't have this method

**File**: `apps/api/src/router/flows/smart_buyer_flow.py`

---

## Fixed Files

### 1. Fixed AgentState (`packages/agent_core/agent_core/models.py`)

```python
# agent_core/agent_core/models.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class StepLog(BaseModel):
    step: str
    kind: str
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None

class AgentState(BaseModel):
    """Unified runtime state for any Agent Flow."""
    session_id: str
    query: str
    # working memory (facts extracted, retrieved data, partial results…)
    facts: Dict[str, Any] = Field(default_factory=dict)
    # execution log
    logs: List[StepLog] = Field(default_factory=list)  # ← FIXED: plural
    # optional conversation context or user profile
    context: Optional[Dict[str, Any]] = None
    # token / cost budget tracking
    budget_tokens: int = 0  # ← FIXED: plural
    spent_tokens: int = 0   # ← FIXED: plural
    # completion flags
    step_idx: int = 0  # ← CONSISTENT: use step_idx everywhere
    done: bool = False
    # final result (structured or plain text)
    output: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "ignore"
    
    def add_log(
        self, 
        kind: str, 
        step: str, 
        input: Any, 
        output: Any, 
        error: Optional[str] = None, 
        latency_ms: Optional[int] = None
    ) -> None:
        self.logs.append(  # ← FIXED: logs not log
            StepLog(
                kind=kind,
                step=step,
                input=input,
                output=output,
                error=error,
                latency_ms=latency_ms,
            )
        )
    
    def mark_done(self, output: Dict[str, Any]) -> None:
        self.output = output
        self.done = True
    
    def use_tokens(self, n: int) -> None:  # ← ADDED: missing method
        """Spend tokens and check budget"""
        self.spent_tokens += n
        if self.budget_tokens > 0 and self.spent_tokens >= self.budget_tokens:
            self.done = True

# convenience helper
def new_agent_state(session_id: str, query: str, budget_tokens: int = 8000) -> AgentState:
    return AgentState(session_id=session_id, query=query, budget_tokens=budget_tokens)
```

---

### 2. Fixed BaseNode (`packages/agent_core/agent_core/nodes/base.py`)

```python
# quantumx-ai/packages/agent_core/agent_core/nodes/base.py
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from agent_core.agent_core.models import AgentState

class BaseNode(ABC):
    name: str = "base_node"
    cost_per_call_tokens: int = 0

    async def run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        t0 = time.perf_counter()
        error: Optional[str] = None
        input_snapshot: Dict[str, Any] = {
            "ctx": {k: v for k, v in (ctx or {}).items() if k not in {"secrets", "api_key"}},
            "facts_keys": list((state.facts or {}).keys()),
            "step_idx": state.step_idx,  # ← FIXED: consistent naming
        }
        output_snapshot: Optional[Dict[str, Any]] = None

        try:
            if self.cost_per_call_tokens:
                self.spend_tokens(state, self.cost_per_call_tokens)  # ← FIXED: correct method name
            
            new_state = await self._run(state, ctx)
            output_snapshot = self._safe_output_snapshot(new_state)
            return new_state
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            # fail-soft: record error log; caller may decide whether to stop
            state.add_log(kind=self.name, step="error", input=input_snapshot, output=None, error=error)
            return state
        finally:
            latency_ms = int((time.perf_counter() - t0) * 1000)  # ← FIXED: typo was latancy_ms
            state.add_log(
                kind=self.name,
                step="run",
                input=input_snapshot,
                output=output_snapshot,
                error=error,
                latency_ms=latency_ms,
            )
    
    @abstractmethod
    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        """
        Subclasses implement their logic here.
        Must return the (possibly updated) `state`.
        """
        ...
    
    # --------- Helpers ---------
    def spend_tokens(self, state: AgentState, n: int) -> None:  # ← FIXED: correct name
        if n <= 0:
            return
        state.use_tokens(n)
    
    def _safe_output_snapshot(self, state: AgentState) -> Dict[str, Any]:
        facts_keys: List[str] = list((state.facts or {}).keys())  # ← FIXED: syntax
        out = {
            "facts_keys": facts_keys,
            "done": state.done,
            "step_idx": state.step_idx,  # ← FIXED: consistent
        }
        if state.output is not None:
            try:
                out["output_keys"] = list(state.output.keys())
            except Exception:
                out["output_present"] = True
        return out
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
```

---

### 3. Fixed SmartBuyerFlow (`apps/api/src/router/flows/smart_buyer_flow.py`)

```python
# quantumx-ai/apps/api/src/router/flows/smart_buyer_flow.py
from __future__ import annotations

import asyncio
import time
from typing import List, Optional, Dict, Any

from packages.agent_core.agent_core.models import AgentState
from packages.agent_core.agent_core.planner import build_initial_plan
from packages.agent_core.agent_core.nodes.price_compare import PriceCompareNode
from packages.tools.tools.registry import ToolRegistry
from packages.llm_client.llm_client.base import ILLMClient
from packages.memory_core.memory_core.base import IMemory
from packages.agent_core.agent_core.nodes.base import BaseNode
from packages.agent_core.agent_core.profiles.smart_buyer_profile import SmartBuyerProfile
from packages.agent_core.agent_core.nodes.explain import ExplainNode
from packages.agent_core.agent_core.nodes.decision import DecisionNode
from packages.agent_core.agent_core.nodes.finalize import FinalizeNode


class SmartBuyerFlow:
    """
    LangGraph-style orchestrator for Smart Buyer agent.
    
    Pipeline: search → score → explain → finalize
    
    Key Features:
    - Dynamic planning via LLM
    - Stateful execution (AgentState flows through nodes)
    - Budget enforcement (token limits)
    - Observability (logs each step)
    - Fail-soft error handling
    """
    
    name = "smart_buyer"
    
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
        self._built = False  # ← FIXED: was _build
    
    async def build(self, state: AgentState) -> Dict[str, Any]:
        """Build execution plan and instantiate nodes"""
        plan = await build_initial_plan(
            self.llm, 
            self.profile, 
            self.tools, 
            self.memory, 
            state
        )
        self.nodes = self._instantiate_nodes(plan.steps)  # ← FIXED: call on self, not plan
        self._built = True
        return {"plan": plan.model_dump(mode="json")}
    
    async def run(self, state: AgentState, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the flow with timeout protection"""
        if not self._built:
            await self.build(state)
        timeout_s = float(ctx.get("timeout_s", self.default_timeout_s))
        return await asyncio.wait_for(self._run_nodes(state, ctx), timeout=timeout_s)  # ← FIXED: method name
    
    async def _run_nodes(self, state: AgentState, ctx: Dict[str, Any]) -> Dict[str, Any]:  # ← FIXED: renamed from _run_inner
        """Execute nodes sequentially (LangGraph-style)"""
        t0 = time.perf_counter()
        
        # Sequential execution with early termination
        for idx, node in enumerate(self.nodes):
            if state.done:
                break
            
            state.step_idx = idx
            state = await node.run(state, ctx)
            
            # Budget enforcement
            if self._budget_exceeded(state):
                state.mark_done({
                    "offers": state.facts.get("offers", []),
                    "scoring": state.facts.get("scoring", {}),
                    "explanation": state.facts.get("explanation", {}),
                    "summary": "budget_exceeded",
                })
                break
        
        # Package output
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
        """
        Convert plan steps into node instances.
        
        This is where you map step kinds/tools to concrete node classes.
        Similar to LangGraph's graph.add_node() calls.
        """
        nodes: List[BaseNode] = []
        
        for s in steps:
            k = getattr(s, "kind", None)
            tool = getattr(s, "tool", None)
            
            # Map plan steps to node types
            if k == "tool" and tool == "price_compare":
                nodes.append(PriceCompareNode(self.tools))
            elif k in ("decide",) or (k == "tool" and tool == "decision_score"):
                nodes.append(DecisionNode(self.tools))
            elif k in ("explain",):
                nodes.append(ExplainNode(self.tools, self.llm))
            elif k in ("finalize",):
                nodes.append(FinalizeNode())
        
        # Fallback to default pipeline if planning failed
        if not nodes:
            nodes = [
                PriceCompareNode(self.tools),
                DecisionNode(self.tools),
                ExplainNode(self.tools, self.llm),
                FinalizeNode()
            ]
        
        # Ensure finalize node at end
        if not isinstance(nodes[-1], FinalizeNode):
            nodes.append(FinalizeNode())
        
        return nodes
    
    def _budget_exceeded(self, state: AgentState) -> bool:
        """Check if token budget has been exceeded"""
        if state.budget_tokens <= 0:
            return False
        return state.spent_tokens >= state.budget_tokens  # ← FIXED: correct field names
```

---

## Enhancements for Multi-Agent Reasoning

### 1. Add Conditional Routing (True LangGraph Feature)

```python
# In BaseNode, add:
async def next_node(self, state: AgentState, ctx: Dict[str, Any]) -> Optional[str]:
    """
    Return name of next node, or None for default sequential.
    This enables conditional branching.
    """
    return None

# Example: Skip explain if no offers
class DecisionNode(BaseNode):
    async def next_node(self, state, ctx):
        if not state.facts.get("offers"):
            return "finalize"  # Skip explain, go straight to finalize
        return None  # Default: continue to next
```

### 2. Add Node Registry Pattern

```python
# Create a node registry for cleaner instantiation
NODE_REGISTRY = {
    "price_compare": PriceCompareNode,
    "decision": DecisionNode,
    "explain": ExplainNode,
    "finalize": FinalizeNode,
}

def _instantiate_nodes(self, steps: List[Any]) -> List[BaseNode]:
    nodes = []
    for s in steps:
        node_cls = NODE_REGISTRY.get(s.tool or s.kind)
        if node_cls:
            # Inject dependencies based on what node needs
            if node_cls in (PriceCompareNode, DecisionNode):
                nodes.append(node_cls(self.tools))
            elif node_cls == ExplainNode:
                nodes.append(node_cls(self.tools, self.llm))
            else:
                nodes.append(node_cls())
    return nodes
```

### 3. Add Parallel Execution (Advanced)

```python
# For nodes that can run in parallel
async def _run_nodes(self, state: AgentState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    for idx, node in enumerate(self.nodes):
        if state.done:
            break
        
        # Check if this is a parallel group
        if isinstance(node, ParallelNodeGroup):
            # Run all nodes in group concurrently
            results = await asyncio.gather(*[
                n.run(state.model_copy(), ctx) for n in node.nodes
            ])
            # Merge results
            state = self._merge_states(state, results)
        else:
            state = await node.run(state, ctx)
```

### 4. Add Retry Logic

```python
class BaseNode(ABC):
    max_retries: int = 0
    retry_delay_s: float = 1.0
    
    async def run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        for attempt in range(self.max_retries + 1):
            try:
                return await self._run(state, ctx)
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay_s * (2 ** attempt))
                    continue
                # Last attempt failed, log and fail-soft
                state.add_log(kind=self.name, step="error", ...)
                return state
```

---

## Testing Your Pipeline

```python
# Test the flow
async def test_smart_buyer_flow():
    from packages.tools.tools.registry import ToolRegistry
    from packages.llm_client.llm_client.local_client import LocalClient
    from packages.agent_core.agent_core.models import AgentState
    
    # Setup
    tools = ToolRegistry()
    llm = LocalClient()
    flow = SmartBuyerFlow(tools=tools, llm=llm)
    
    # Create state
    state = AgentState(
        session_id="test-123",
        query="iPhone 15",
        budget_tokens=5000
    )
    
    # Run flow
    ctx = {"top_k": 5, "request_id": "test-123"}
    result = await flow.run(state, ctx)
    
    print(f"Offers: {len(result['offers'])}")
    print(f"Winner: {result['explanation']['winner']}")
    print(f"Logs: {len(state.logs)} steps")

# Run test
import asyncio
asyncio.run(test_smart_buyer_flow())
```

---

## Summary

Your LangGraph-style architecture is **exactly right** for multi-agent reasoning:

✅ **Stateful execution** - State flows through nodes  
✅ **Modular nodes** - Each node is self-contained  
✅ **Dynamic planning** - LLM generates execution plan  
✅ **Budget control** - Token limits prevent runaway costs  
✅ **Observability** - Every step is logged  

**Just fix the 5 bugs above** and you'll have a production-ready multi-agent orchestrator!

