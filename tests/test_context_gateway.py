from __future__ import annotations

from sparkforge.adapters.tools import TOOLS
from sparkforge.context.gateway import ContextGateway
from sparkforge.context.gateway_budget import serialized_bytes
from sparkforge.context.gateway_models import GatewayProfile, GatewayRequest


def test_gateway_discovers_bounded_capabilities_and_preserves_budget() -> None:
    request = GatewayRequest(
        intent="Glue 5.1 FGAC Iceberg",
        profile=GatewayProfile.ECONOMY,
        max_bytes=5000,
    )

    result = ContextGateway(TOOLS).start(request)

    assert result["status"] == "ok"
    assert len(result["capabilities"]) <= 8
    assert result["budget"]["unit"] == "serialized_utf8_json_bytes"
    assert result["budget"]["payload_bytes"] <= request.max_bytes
    assert serialized_bytes(result) <= request.max_bytes


def test_gateway_keeps_critical_fact_when_low_relevance_context_is_reduced() -> None:
    items = [
        {"id": "noise", "kind": "knowledge", "relevance": 1, "content": "x" * 3000},
        {"fact_id": "f_critical", "kind": "fact", "relevance": 100, "value": "observed"},
    ]
    request = GatewayRequest("diagnose Glue", GatewayProfile.ECONOMY, 2500, items=tuple(items))

    result = ContextGateway(TOOLS).start(request)

    assert result["status"] == "ok"
    assert any(item["id"] == "f_critical" for item in result["context"])
    assert result["budget"]["reductions"]


def test_gateway_returns_named_refusal_when_critical_payload_cannot_fit() -> None:
    request = GatewayRequest(
        "diagnose",
        GatewayProfile.ECONOMY,
        40,
        items=(
            {"fact_id": "f1", "kind": "fact", "evidence": "critical evidence"},
        ),
    )

    result = ContextGateway(TOOLS).start(request)

    assert result["status"] == "refused"
    assert result["error"]
    assert result["unresolved"][0]["code"] == "budget_unresolved"
