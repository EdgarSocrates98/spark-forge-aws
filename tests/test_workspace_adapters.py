from __future__ import annotations

from sparkforge.workspace import (
    SemanticEdge,
    SemanticGraph,
    SemanticNode,
    artifact_graph_fragment,
    semantic_graph_fragment,
    transcript_evidence_fragment,
)
from sparkforge.workspace.freshness import FreshnessAssessment


def test_semantic_adapter_preserves_records_metadata_and_freshness() -> None:
    semantic = SemanticGraph(
        nodes=(SemanticNode("job:daily", "job", "daily", "repo"),),
        edges=(SemanticEdge("job:daily", "writes", "dataset:orders", "repo", 12, 0.9),),
        unresolved=({"code": "dynamic_reference", "repository": "repo"},),
        manifest_fingerprint="manifest",
        freshness=FreshnessAssessment("stale", "current", "indexed", "fingerprint_mismatch"),
    )

    fragment = semantic_graph_fragment(semantic, source_id="semantic:repo")

    assert fragment.source_id == "semantic:repo"
    assert fragment.source_kind == "semantic"
    assert fragment.nodes == (
        {"id": "job:daily", "kind": "job", "label": "daily", "repository": "repo"},
    )
    assert fragment.edges == (
        {
            "source": "job:daily",
            "relation": "writes",
            "target": "dataset:orders",
            "repository": "repo",
            "line": 12,
            "confidence": 0.9,
        },
    )
    assert fragment.unresolved == ({"code": "dynamic_reference", "repository": "repo"},)
    assert fragment.freshness.status == "stale"


def test_artifact_adapter_keeps_only_declared_edges_and_provenance() -> None:
    fragment = artifact_graph_fragment(
        {
            "graph": {
                "nodes": [
                    {"id": "dataset:orders", "kind": "dataset", "label": "orders"},
                    {"id": "cloud:orders", "kind": "cloud_resource", "label": "orders"},
                ],
                "edges": [
                    {
                        "source": "dataset:orders",
                        "relation": "corresponds_to",
                        "target": "cloud:orders",
                    }
                ],
            },
            "provenance": [{"artifact": "workspace-graph.json"}],
            "unresolved": [{"code": "access_denied", "resource_id": "orders"}],
            "current_fingerprint": "same",
            "indexed_fingerprint": "same",
        },
        source_id="aws:orders",
    )

    assert fragment.source_kind == "aws_artifact"
    assert fragment.edges == (
        {
            "source": "dataset:orders",
            "relation": "corresponds_to",
            "target": "cloud:orders",
        },
    )
    assert fragment.provenance == ({"artifact": "workspace-graph.json"},)
    assert fragment.unresolved == ({"code": "access_denied", "resource_id": "orders"},)
    assert fragment.freshness.status == "fresh"


def test_transcript_adapter_does_not_derive_graph_relationships() -> None:
    fragment = transcript_evidence_fragment(
        {
            "nodes": [
                {"id": "run:daily", "kind": "job"},
                {"id": "dataset:orders", "kind": "dataset"},
            ],
            "provenance": [{"transcript": "fixture"}],
            "unresolved": [{"code": "tokens_unresolved"}],
        },
        source_id="transcript:daily",
    )

    assert fragment.source_kind == "provider_transcript"
    assert fragment.edges == ()
    assert fragment.provenance == ({"transcript": "fixture"},)
    assert fragment.unresolved == ({"code": "tokens_unresolved"},)
