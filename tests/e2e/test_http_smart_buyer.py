from __future__ import annotations

from tests.e2e.helpers import assert_smart_buyer_payload


def test_http_smart_buyer_flow(fastapi_client, api_prefix) -> None:
    payload = {
        "query": "iphone 15",
        "top_k": 3,
        "prefs": {"option_label": "deal hunter"},
        "criteria": [
            {"name": "price", "weight": 0.6, "maximize": False},
            {"name": "rating", "weight": 0.4, "maximize": True},
        ],
    }
    headers = {
        "x-org-id": "org_demo",
        "x-user-id": "user_e2e",
        "x-user-role": "admin",
        "x-channel": "test",
    }

    response = fastapi_client.post(f"{api_prefix}/smart-buyer", json=payload, headers=headers)

    assert response.status_code == 200
    body = response.json()

    assert body["query"] == payload["query"]
    assert body["metadata"]["top_k"] == payload["top_k"]
    assert body["request_id"], "request_id should be returned to caller"
    assert body["latency_ms"] >= 0

    assert_smart_buyer_payload(body, expected_top_k=payload["top_k"])

