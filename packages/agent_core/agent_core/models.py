# agent_core/agent_core/models.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepLog(BaseModel):
    step: str
    kind: str
    node: Optional[str] = None
    tool: Optional[str] = None
    input: Optional[Any] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None


class AgentState(BaseModel):
    """Unified runtime state for any Agent Flow (state-first)."""

    # identity
    session_id: str
    query: str
    trace_id: Optional[str] = None

    # working memory
    facts: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # reasoning / search
    thoughts: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    search_nodes: List[Dict[str, Any]] = Field(default_factory=list)

    # logging / diagnostics
    log: List[StepLog] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    # budget
    budget_token: int = 0
    spent_token: int = 0

    # execution control
    step_index: int = 0
    current_node: Optional[str] = None
    active_tool: Optional[str] = None
    done: bool = False
    halted: bool = False

    # final result
    output: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "ignore"

    def add_log(
        self,
        kind: str,
        step: str,
        input: Any = None,
        output: Any = None,
        error: Optional[str] = None,
        latency_ms: Optional[int] = None,
        node: Optional[str] = None,
        tool: Optional[str] = None,
    ) -> None:
        self.log.append(
            StepLog(
                kind=kind,
                step=step,
                node=node or self.current_node,
                tool=tool or self.active_tool,
                input=input,
                output=output,
                error=error,
                latency_ms=latency_ms,
            )
        )

    def add_thought(self, text: str) -> None:
        self.thoughts.append(text)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def mark_done(self, output: Dict[str, Any]) -> None:
        self.output = output
        self.done = True

    def halt(self, reason: str, output: Optional[Dict[str, Any]] = None) -> None:
        self.halted = True
        self.errors.append(reason)
        self.metadata["halt_reason"] = reason
        if output is not None:
            self.output = output

    def use_tokens(self, n: int) -> None:
        self.spent_token += n
        if self.budget_token > 0 and self.spent_token > self.budget_token:
            self.halted = True
            self.errors.append("token_budget_exceeded")

    # Backwards-compatible alias (typo kept for legacy callers)
    def user_token(self, n: int) -> None:
        self.use_tokens(n)

    def next_step(self, node: Optional[str] = None) -> None:
        self.step_index += 1
        if node is not None:
            self.current_node = node

    def start_tool(self, tool_name: str) -> None:
        self.active_tool = tool_name

    def end_tool(self) -> None:
        self.active_tool = None


def new_agent_state(
    session_id: str,
    query: str,
    budget_token: int = 8000,
    context: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> AgentState:
    return AgentState(
        session_id=session_id,
        query=query,
        budget_token=budget_token,
        context=context,
        trace_id=trace_id,
    )
