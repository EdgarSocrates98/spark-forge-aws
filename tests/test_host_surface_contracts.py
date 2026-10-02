from __future__ import annotations

from sparkforge.adapters.mcp import tools_do_transporte
from sparkforge.adapters.tools import TOOLS, call_tool


def test_full_and_compact_surfaces_have_declared_sizes() -> None:
    assert len(tools_do_transporte("stdio", "full")) == 120
    assert len(tools_do_transporte("stdio", "compact")) == 7
    assert len(tools_do_transporte("http", "compact")) == 7


def test_gateway_envelope_is_shared_and_provider_tokens_remain_separate() -> None:
    payload = call_tool(
        "sparkforge_context_start",
        {"intent": "Glue FGAC", "profile": "economy", "max_bytes": 6000},
    )
    assert payload["schema_version"] == 1
    assert "execution_plan" in payload
    assert "context_tree" in payload
    assert payload["context_tree"]["tokens"]["status"] == "unresolved"
    assert payload["provider_tokens"] is None
    assert "sparkforge_context_start" in TOOLS
