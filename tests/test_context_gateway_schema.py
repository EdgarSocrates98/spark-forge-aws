from __future__ import annotations

import jsonschema

from sparkforge_aws.adapters.tools import TOOLS, call_tool
from sparkforge_aws.context.schemas import load_gateway_schema


def test_gateway_schema_accepts_cli_core_envelope() -> None:
    result = call_tool(
        "sparkforge_context_start",
        {"intent": "Glue 5.1", "profile": "economy", "max_bytes": 5000},
    )

    jsonschema.validate(result, load_gateway_schema())


def test_gateway_mcp_output_schema_matches_shared_contract() -> None:
    result = call_tool(
        "sparkforge_context_start",
        {"intent": "Iceberg", "profile": "balanced", "max_bytes": 5000},
    )

    jsonschema.validate(result, TOOLS["sparkforge_context_start"]["outputSchema"])


def test_gateway_uses_profile_default_when_max_bytes_is_omitted() -> None:
    result = call_tool(
        "sparkforge_context_start",
        {"intent": "Iceberg", "profile": "economy"},
    )

    assert result["budget"]["max_bytes"] == 6000
    assert result["answer_state"]["status"] == "unavailable"
