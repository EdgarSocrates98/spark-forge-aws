from __future__ import annotations

from sparkforge_aws.workspace import (
    SemanticEdge,
    SemanticGraph,
    SemanticNode,
    compose_workspace_graph,
)


def test_static_and_live_graph_compose_with_explicit_bridge() -> None:
    semantic = SemanticGraph(
        nodes=(
            SemanticNode("repo:orders", "repository", "orders", "orders"),
            SemanticNode(
                "orders:data:dataset:orders",
                "dataset",
                "orders",
                "orders",
            ),
        ),
        edges=(
            SemanticEdge(
                "repo:orders",
                "observes",
                "orders:data:dataset:orders",
                "orders",
            ),
        ),
        unresolved=(),
        manifest_fingerprint="semantic-fp",
    )
    live = {
        "source_id": "aws:live",
        "source_kind": "aws_artifact",
        "provenance": [{"source_id": "aws:live", "collected_at": "2026-09-27T00:00:00Z"}],
        "unresolved": [{"reason": "cross_account_role_required", "resource_id": "orders"}],
        "graph": {
            "nodes": [
                {"id": "account:222222222222", "kind": "account"},
                {"id": "glue_table:orders", "kind": "glue_table"},
                {"id": "lakeformation:orders", "kind": "lakeformation"},
                {"id": "s3_prefix:orders", "kind": "s3_prefix"},
            ],
            "edges": [
                {
                    "source": "glue_table:orders",
                    "relation": "governed_by",
                    "target": "lakeformation:orders",
                },
                {
                    "source": "glue_table:orders",
                    "relation": "stored_at",
                    "target": "s3_prefix:orders",
                },
            ],
        },
    }

    graph = compose_workspace_graph(
        semantic,
        live,
        bridges=(
            {
                "source": "orders:data:dataset:orders",
                "relation": "corresponds_to",
                "target": "glue_table:orders",
            },
        ),
    )

    node_ids = {node["id"] for node in graph.nodes}
    assert {
        "orders:data:dataset:orders",
        "glue_table:orders",
        "lakeformation:orders",
        "s3_prefix:orders",
    } <= node_ids
    assert {
        (edge["source"], edge["relation"], edge["target"])
        for edge in graph.edges
    } >= {
        ("orders:data:dataset:orders", "corresponds_to", "glue_table:orders"),
        ("glue_table:orders", "governed_by", "lakeformation:orders"),
        ("glue_table:orders", "stored_at", "s3_prefix:orders"),
    }
    assert {item.get("reason") for item in graph.unresolved} >= {
        "cross_account_role_required"
    }
    assert graph.sources == ("aws:live", "manifest:workspace", "semantic:workspace")

    without_bridge = compose_workspace_graph(semantic, live)
    assert not any(edge.get("relation") == "corresponds_to" for edge in without_bridge.edges)
