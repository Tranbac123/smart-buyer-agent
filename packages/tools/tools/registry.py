from __future__ import annotations

"""
Compatibility shim: legacy modules still import `packages.tools.tools.registry`.
We now re-export the canonical ControlPlane ToolRegistry from
`packages.control_plane.control_plane.tool_registry`.
"""

from packages.control_plane.control_plane.tool_registry import ToolRegistry

__all__ = ["ToolRegistry"]


