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
    log: List[StepLog] = Field(default_factory=list)
    # optional conversation context or user profile
    context: Optional[Dict[str, Any]] = None
    # token / cost budget tracking
    budget_token: int = 0
    spent_token: int = 0
    # completion flags
    step_index: int = 0
    done: bool = False
    # final result (structured or plain text)
    output: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "ignore"
    
    def add_log(self, kind: str, step: str, input: Any, output: Any, error: str | None = None, latency_ms: str | None = None) -> None:
        self.log.append(
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
    def user_token(self, n: int) -> None:
        self.spent_token += n
        if self.spent_token > self.budget_token:
            self.done = True
# convenience helper
def new_agent_state(session_id: str, query: str, budget_token: int = 8000) -> AgentState:
    return AgentState(session_id=session_id, query=query, budget_token=budget_token)
