"""Compose static workspace semantics with explicitly collected live graph data."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sparkforge.workspace.adapters import artifact_graph_fragment, semantic_graph_fragment
from sparkforge.workspace.federated import FederatedGraph, GraphFragment, compose_federated_graph
from sparkforge.workspace.manifest import GraphLink, WorkspaceManifest
from sparkforge.workspace.semantic import build_semantic_graph


def compose_workspace_graph(
    static_graph: Any,
    live_artifact: Mapping[str, Any] | Any,
    *,
    bridges: tuple[GraphLink | Mapping[str, Any], ...] | list[GraphLink | Mapping[str, Any]] = (),
    max_nodes: int = 10000,
    max_edges: int = 20000,
    max_provenance: int = 20000,
    max_unresolved: int = 10000,
) -> FederatedGraph:
    """Compose static and live fragments; cross-source edges require explicit bridges."""

    bridge_edges = tuple(_bridge_record(item) for item in bridges)
    fragments = (
        semantic_graph_fragment(static_graph, "semantic:workspace"),
        artifact_graph_fragment(live_artifact, "aws:live"),
        GraphFragment(
            source="manifest:workspace",
            source_id="manifest:workspace",
            source_kind="federated_links",
            edges=bridge_edges,
            provenance=({"source_id": "manifest:workspace", "kind": "federated_links"},),
        ),
    )
    return compose_federated_graph(
        fragments,
        max_nodes=max_nodes,
        max_edges=max_edges,
        max_provenance=max_provenance,
        max_unresolved=max_unresolved,
    )


def compose_manifest_graph(
    manifest: WorkspaceManifest,
    live_artifact: Mapping[str, Any] | Any,
    *,
    databases: Mapping[str, Any] | None = None,
    max_nodes: int = 10000,
    max_edges: int = 20000,
    max_provenance: int = 20000,
    max_unresolved: int = 10000,
) -> FederatedGraph:
    """Build static graph from manifest and compose it with a live collection."""

    static_graph = build_semantic_graph(
        manifest,
        databases=databases,
        max_nodes=max_nodes,
    )
    return compose_workspace_graph(
        static_graph,
        live_artifact,
        bridges=manifest.federated_links,
        max_nodes=max_nodes,
        max_edges=max_edges,
        max_provenance=max_provenance,
        max_unresolved=max_unresolved,
    )


def _bridge_record(value: GraphLink | Mapping[str, Any]) -> dict[str, str]:
    if isinstance(value, GraphLink):
        source, relation, target = value.source, value.relation, value.target
    elif isinstance(value, Mapping):
        source = value.get("source")
        relation = value.get("relation")
        target = value.get("target")
    else:
        raise TypeError("federated bridge must be a GraphLink or mapping")
    if not all(isinstance(item, str) and item.strip() for item in (source, relation, target)):
        raise ValueError("federated bridge source, relation and target are required")
    return {"source": source.strip(), "relation": relation.strip(), "target": target.strip()}


__all__ = ["compose_manifest_graph", "compose_workspace_graph"]
