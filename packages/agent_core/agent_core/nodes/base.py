# quantumx-ai/packages/agent_core/agent_core/nodes/base.py
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
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
            "step_index": state.step_index,
        }
        output_snapshot: Optional[Dict[str, Any]] = None

        try:
            if self.cost_per_call_tokens:
                self.spent_tokens(state, self.cost_per_call_tokens)
            
            new_state = await self._run(state, ctx)
            output_snapshot = self._safe_output_snapshot(new_state)
            return new_state
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            # fail-soft: record error log; caller may decide whether to stop
            state.add_log(kind=self.name, step="error", input=input_snapshot, output=None, error=error)
            return state
        finally:
            latancy_ms = int((time.perf_counter() - t0) * 1000)
            state.add_log(
                kind=self.name,
                step="run",
                input=input_snapshot,
                output=output_snapshot,
                error=error,
                latency_ms=latancy_ms,
            )
    @abstractmethod
    async def _run(self, state: AgentState, ctx: Dict[str, Any]) -> AgentState:
        """
        Subclasses implement their logic here.
        Must return the (possibly updated) `state`.
        """
        ...
    # --------- Helpers ---------
    def spend_tokens(self, state: AgentState, n: int) -> None:
        if n <= 0:
            return
        state.use_tokens(n)
    
    def _safe_output_snapshot(self, state: AgentState) -> Dict[str, Any]:
        facts_keys = list[str]((state.facts or {}).keys())
        out = {
            "facts_keys": facts_keys,
            "done": state.done,
            "step_index": state.step_index,
        }
        if state.output is not None:
            try:
                out["output_keys"] = list(state.output.keys())
            except Exception:
                out["output_present"] = True
        return out
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"

