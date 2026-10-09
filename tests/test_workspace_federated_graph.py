from __future__ import annotations

from sparkforge_aws.workspace import (
    FreshnessAssessment,
    GraphAdapter,
    GraphFragment,
    compose_federated_graph,
)
from sparkforge_aws.workspace.graph import WorkspaceGraph, WorkspaceNode


def test_federated_graph_is_deterministic_and_preserves_evidence() -> None:
    code = GraphFragment(
        source="code",
        nodes=({"id": "repo:job", "kind": "repository"},),
        edges=(),
        provenance=({"artifact": "codeintel.sqlite3"},),
        unresolved=({"code": "dynamic_reference"},),
        freshness=FreshnessAssessment("fresh", "same", "same", "fingerprint_match"),
    )
    workspace = GraphFragment(
        source="workspace",
        nodes=({"id": "repo:lib", "kind": "repository"},),
        edges=({"source": "repo:job", "relation": "uses", "target": "repo:lib"},),
        provenance=({"artifact": "workspace.yaml"},),
        freshness=FreshnessAssessment("fresh", "same", "same", "fingerprint_match"),
    )

    first = compose_federated_graph([workspace, code])
    second = compose_federated_graph([code, workspace])

    assert first.to_dict() == second.to_dict()
    assert first.neighbors("repo:job") == ("repo:lib",)
    assert {item["artifact"] for item in first.provenance} == {
        "codeintel.sqlite3",
        "workspace.yaml",
    }
    assert {item["code"] for item in first.unresolved} == {"dynamic_reference"}
    assert first.freshness.status == "fresh"


def test_federated_graph_does_not_invent_cross_fragment_edges() -> None:
    graph = compose_federated_graph(
        [
            GraphFragment(source="left", nodes=({"id": "left:item"},)),
            GraphFragment(source="right", nodes=({"id": "right:item"},)),
        ]
    )

    assert graph.edges == ()
    assert graph.unresolved == ()


def test_federated_graph_bounds_nodes_and_keeps_unresolved_state() -> None:
    fragment = GraphFragment(
        source="bounded",
        nodes=tuple({"id": f"node:{index}"} for index in range(3)),
        unresolved=({"code": "source_blind_spot"},),
    )

    graph = compose_federated_graph([fragment], max_nodes=2)

    assert len(graph.nodes) == 2
    assert graph.truncated is True
    assert all("id" in node for node in graph.nodes)
    assert {item["code"] for item in graph.unresolved} >= {"source_blind_spot"}
    assert {item["code"] for item in graph.unresolved} >= {"graph_nodes_truncated"}


def test_federated_graph_bounds_each_collection_and_names_truncation() -> None:
    fragment = GraphFragment(
        source="bounded",
        nodes=({"id": "node:0"}, {"id": "node:1"}),
        edges=({"source": "node:0", "relation": "links", "target": "node:1"},),
        provenance=({"artifact": "a"}, {"artifact": "b"}),
        unresolved=({"code": "source_blind_spot"},),
    )

    graph = compose_federated_graph(
        [fragment], max_edges=1, max_provenance=1, max_unresolved=1
    )

    assert len(graph.edges) == 1
    assert len(graph.provenance) == 1
    assert len(graph.unresolved) == 1
    assert graph.truncated is True


def test_graph_adapter_is_explicit_and_missing_freshness_stays_unknown() -> None:
    adapter = GraphAdapter(
        "adapter",
        builder=lambda: GraphFragment(nodes=({"id": "node"},)),
    )

    graph = compose_federated_graph(adapters=[adapter])

    assert graph.sources == ("adapter",)
    assert graph.nodes == ({"id": "node"},)
    assert graph.freshness.status == "unknown"


def test_existing_workspace_dataclasses_become_graph_fragment_records() -> None:
    workspace = WorkspaceGraph(
        nodes=(WorkspaceNode("repo:a", "repository", "fingerprint", True),),
        edges=(),
        unresolved=(),
        manifest_fingerprint="manifest",
    )

    graph = compose_federated_graph([workspace])

    assert graph.nodes == (
        {
            "id": "repo:a",
            "kind": "repository",
            "fingerprint": "fingerprint",
            "exists": True,
        },
    )
