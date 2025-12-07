from __future__ import annotations

from fastapi import Depends

from dependencies.control_plane_provider import get_control_plane
from packages.control_plane.control_plane.core import ControlPlane
from services.orchestrator_service import OrchestratorService


def get_orchestrator_service(
    control_plane: ControlPlane = Depends(get_control_plane),
) -> OrchestratorService:
    return OrchestratorService(control_plane=control_plane)




