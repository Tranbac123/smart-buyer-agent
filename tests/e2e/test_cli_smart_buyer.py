from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.e2e.helpers import assert_smart_buyer_payload, extract_json_from_mixed_output


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI_SCRIPT = PROJECT_ROOT / "apps" / "api" / "src" / "cli" / "run_smart_buyer.py"


def _build_cli_env() -> dict[str, str]:
    env = os.environ.copy()
    search_paths = [
        str(PROJECT_ROOT),
        str(PROJECT_ROOT / "apps" / "api" / "src"),
        str(PROJECT_ROOT / "packages"),
    ]
    existing = env.get("PYTHONPATH")
    if existing:
        search_paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(search_paths)
    return env


def test_cli_smart_buyer_flow() -> None:
    cmd = [
        sys.executable,
        str(CLI_SCRIPT),
        "--query",
        "iphone 15",
        "--top-k",
        "3",
        "--timeout",
        "10",
    ]

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        env=_build_cli_env(),
    )

    payload = extract_json_from_mixed_output(completed.stdout)
    assert_smart_buyer_payload(payload, expected_top_k=3)

    metadata = payload["metadata"]
    assert metadata.get("channel") == "cli"
    assert metadata.get("flow_name") == "smart_buyer"


