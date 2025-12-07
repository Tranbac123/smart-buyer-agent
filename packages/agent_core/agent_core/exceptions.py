# packages/agent_core/agent_core/exceptions.py

from __future__ import annotations
from typing import Optional


class AgentRuntimeError(Exception):
    """Base error for agent runtime (nodes, flows, orchestrator)."""


class NodeExecutionError(AgentRuntimeError):
    def __init__(
        self,
        node_name: str,
        message: str,
        *,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(f"[{node_name}] {message}")
        self.node_name = node_name
        self.cause = cause


class InvalidStateError(AgentRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class FlowHaltError(AgentRuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Flow halted: {reason}")
        self.reason = reason


class StepNotAllowedError(AgentRuntimeError):
    def __init__(self, step_name: str, reason: str) -> None:
        super().__init__(f"Step '{step_name}' is not allowed: {reason}")
        self.step_name = step_name
        self.reason = reason
