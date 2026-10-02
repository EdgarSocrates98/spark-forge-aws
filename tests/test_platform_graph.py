"""Contract tests for the offline platform intelligence graph."""

from __future__ import annotations

import json
from pathlib import Path

from sparkforge.adapters import _core
from sparkforge.adapters.tools import call_tool
from sparkforge.platform.graph import analyze_platform_graph, load_platform_graph


FIXTURE = Path(__file__).parents[1] / "fixtures" / "platform" / "graph.yaml"


def test_platform_graph_loads_and_fingerprints_deterministically(tmp_path: Path) -> None:
    graph = load_platform_graph(FIXTURE)
    result = analyze_platform_graph(FIXTURE)

    assert len(graph.nodes) == 6
    assert len(graph.edges) == 5
    assert result["graph"]["fingerprint"] == graph.fingerprint
    assert graph.unresolved == ()

    equivalent = tmp_path / "graph.json"
    equivalent.write_text(json.dumps(graph.to_dict()), encoding="utf-8")
    assert load_platform_graph(equivalent).fingerprint == graph.fingerprint


def test_platform_graph_impact_preserves_paths_and_unresolved() -> None:
    result = analyze_platform_graph(
        FIXTURE,
        changed_node="postgres.orders",
        changed_attribute="primary_key",
        direction="downstream",
        max_depth=10,
    )
    impact = result["impact"]

    assert impact["direct"] == ["debezium.orders"]
    assert "athena.orders" in impact["transitive"]
    assert impact["paths"][-1]["nodes"][0] == "postgres.orders"
    assert impact["unresolved"] == []

    missing = analyze_platform_graph(FIXTURE, changed_node="missing.node")["impact"]
    assert {item["code"] for item in missing["unresolved"]} == {
        "platform_impact_node_unresolved"
    }


def test_platform_graph_cli_and_mcp_share_contract() -> None:
    cli = _core.analyze_platform_graph(FIXTURE, changed_node="postgres.orders")
    mcp = call_tool(
        "sparkforge_analyze_platform_graph",
        {"path": str(FIXTURE), "changed_node": "postgres.orders"},
    )

    assert mcp["graph"]["fingerprint"] == cli["graph"]["fingerprint"]
    assert mcp["impact"]["affected"] == cli["impact"]["affected"]


def test_platform_graph_reference_is_registered() -> None:
    from sparkforge.adapters.tools import TOOLS

    assert "sparkforge_analyze_platform_graph" in TOOLS
