from __future__ import annotations

import json
from typing import Any, Dict


def assert_smart_buyer_payload(payload: Dict[str, Any], *, expected_top_k: int) -> None:
    offers = payload.get("offers")
    assert isinstance(offers, list) and offers, "expected non-empty offers list"
    assert len(offers) <= max(1, expected_top_k), "offers should respect requested top_k"

    sample_offer = offers[0]
    for field in ("title", "site", "price", "url"):
        assert field in sample_offer, f"offer missing '{field}'"

    scoring = payload.get("scoring")
    assert isinstance(scoring, dict), "scoring bundle missing"
    option_scores = scoring.get("option_scores")
    assert isinstance(option_scores, list) and option_scores, "option_scores must be populated"

    explanation = payload.get("explanation")
    assert isinstance(explanation, dict), "explanation missing"
    assert isinstance(explanation.get("summary", ""), str), "explanation summary must be a string"

    metadata = payload.get("metadata")
    assert isinstance(metadata, dict), "metadata missing"
    assert metadata.get("flow") == "smart_buyer", "unexpected flow metadata"
    assert metadata.get("request_id"), "request_id missing in metadata"


def extract_json_from_mixed_output(raw_output: str) -> Dict[str, Any]:
    """
    CLI runs emit log lines before the JSON payload. This helper slices the
    output from the first '{' to the last '}' so json.loads can parse it.
    """
    start = raw_output.find("{")
    end = raw_output.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate JSON payload in CLI output")
    snippet = raw_output[start : end + 1]
    return json.loads(snippet)


