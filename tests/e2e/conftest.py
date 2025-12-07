from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_SRC = PROJECT_ROOT / "apps" / "api" / "src"
PACKAGES_DIR = PROJECT_ROOT / "packages"


def _ensure_sys_path(path: Path) -> None:
    as_str = str(path)
    if as_str not in sys.path:
        sys.path.insert(0, as_str)


for candidate in (PROJECT_ROOT, API_SRC, PACKAGES_DIR):
    _ensure_sys_path(candidate)

from main import app  # type: ignore  # pylint: disable=wrong-import-position
from api.http_gateway import _api_prefix  # pylint: disable=protected-access


@pytest.fixture(scope="session")
def fastapi_client() -> TestClient:
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def api_prefix() -> str:
    return _api_prefix()

