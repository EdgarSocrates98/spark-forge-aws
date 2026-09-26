from __future__ import annotations

from sparkforge.adapters.tools import TOOLS
from sparkforge.context.gateway import ContextGateway
from sparkforge.context.gateway_models import GatewayProfile, GatewayRequest


def test_fixture_like_case_reports_bytes_separately_from_host_tokens() -> None:
    request = GatewayRequest(
        "Glue OOM with Iceberg small files",
        GatewayProfile.BALANCED,
        12000,
        host_usage={"provider": "fixture-host", "input_tokens": 321},
        items=(
            {"fact_id": "f1", "kind": "fact", "relevance": 100, "measure": 12},
            {"rule_id": "SF-WASTE-001", "kind": "rule", "relevance": 95, "risk": "small files"},
            {"kind": "knowledge", "relevance": 70, "content": "Iceberg compaction guidance" * 40},
        ),
    )

    result = ContextGateway(TOOLS).start(request)

    assert result["budget"]["unit"] == "serialized_utf8_json_bytes"
    assert result["provider_tokens"] == {"provider": "fixture-host", "input_tokens": 321}
    assert "estimated_tokens" not in result["budget"]
