# packages/control_plane/control_plane/exceptions.py

from __future__ import annotations
from typing import Optional


class ControlPlaneError(Exception):
    """Base error for ControlPlane-related failures."""


class PolicyDenyError(ControlPlaneError):
    def __init__(
        self,
        message: str,
        *,
        rule_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.rule_id = rule_id
        self.org_id = org_id


class QuotaExceededError(ControlPlaneError):
    def __init__(
        self,
        message: str = "Quota exceeded",
        *,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.org_id = org_id
        self.user_id = user_id


class UnauthorizedToolError(ControlPlaneError):
    def __init__(
        self,
        tool_name: str,
        message: str | None = None,
    ) -> None:
        if message is None:
            message = f"Tool '{tool_name}' is not allowed"
        super().__init__(message)
        self.tool_name = tool_name


class ToolNotFoundError(ControlPlaneError):
    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' not found")
        self.tool_name = tool_name


class InvalidToolInputError(ControlPlaneError):
    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(f"Invalid input for tool '{tool_name}': {reason}")
        self.tool_name = tool_name
        self.reason = reason
