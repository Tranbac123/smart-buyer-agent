from __future__ import annotations

from packages.control_plane.bootstrap import get_control_plane as _get_control_plane
from packages.control_plane.control_plane.core import ControlPlane


def get_control_plane() -> ControlPlane:
    return _get_control_plane()




