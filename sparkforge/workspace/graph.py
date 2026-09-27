"""Bounded graph over declared workspace repositories and relationships."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sparkforge.workspace.manifest import WorkspaceManifest


@dataclass(frozen=True, slots=True)
class WorkspaceNode:
    id: str
    kind: str
    fingerprint: str
    exists: bool


@dataclass(frozen=True, slots=True)
class WorkspaceEdge:
    source: str
    relation: str
    target: str
    resolved: bool


@dataclass(frozen=True, slots=True)
class WorkspaceGraph:
    nodes: tuple[WorkspaceNode, ...]
    edges: tuple[WorkspaceEdge, ...]
    unresolved: tuple[dict[str, str], ...]

    def neighbors(self, node_id: str, max_depth: int = 2) -> tuple[str, ...]:
        if max_depth < 0:
            return ()
        seen = {node_id}
        frontier = [node_id]
        for _ in range(max_depth):
            next_frontier: list[str] = []
            for edge in self.edges:
                if edge.source in frontier and edge.target not in seen and edge.resolved:
                    seen.add(edge.target)
                    next_frontier.append(edge.target)
            frontier = next_frontier
            if not frontier:
                break
        return tuple(sorted(seen - {node_id}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "nodes": [
                {
                    "id": node.id,
                    "kind": node.kind,
                    "fingerprint": node.fingerprint,
                    "exists": node.exists,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "relation": edge.relation,
                    "target": edge.target,
                    "resolved": edge.resolved,
                }
                for edge in self.edges
            ],
            "unresolved": list(self.unresolved),
        }


def build_graph(manifest: WorkspaceManifest) -> WorkspaceGraph:
    nodes = tuple(
        WorkspaceNode(repo.name, "repository", repo.fingerprint, repo.exists)
        for repo in manifest.repositories
    )
    declared = {node.id for node in nodes}
    edges: list[WorkspaceEdge] = []
    unresolved: list[dict[str, str]] = []
    for relationship in manifest.relationships:
        target = manifest.repository(relationship.target)
        resolved = relationship.target in declared and target is not None and target.exists
        edges.append(
            WorkspaceEdge(
                relationship.source,
                relationship.relation,
                relationship.target,
                resolved,
            )
        )
        if not resolved:
            unresolved.append(
                {
                    "code": "workspace_repository_unresolved",
                    "source": relationship.source,
                    "target": relationship.target,
                }
            )
    return WorkspaceGraph(nodes, tuple(edges), tuple(unresolved))


__all__ = ["WorkspaceEdge", "WorkspaceGraph", "WorkspaceNode", "build_graph"]
