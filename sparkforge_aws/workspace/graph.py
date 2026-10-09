"""Bounded graph over declared workspace repositories and relationships."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from sparkforge_aws.workspace.freshness import FreshnessAssessment
from sparkforge_aws.workspace.manifest import WorkspaceManifest


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
    manifest_fingerprint: str = ""
    freshness: FreshnessAssessment = field(default_factory=FreshnessAssessment.unknown)

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
            "manifest_fingerprint": self.manifest_fingerprint,
            "freshness": self.freshness.status,
            "freshness_detail": self.freshness.to_dict(),
        }


def build_graph(
    manifest: WorkspaceManifest,
    *,
    freshness: FreshnessAssessment | None = None,
) -> WorkspaceGraph:
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
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "nodes": [(node.id, node.fingerprint, node.exists) for node in nodes],
                "edges": [
                    (edge.source, edge.relation, edge.target, edge.resolved)
                    for edge in edges
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return WorkspaceGraph(
        nodes,
        tuple(edges),
        tuple(unresolved),
        fingerprint,
        freshness or FreshnessAssessment.unknown("codeintel_freshness_not_assessed"),
    )


__all__ = ["WorkspaceEdge", "WorkspaceGraph", "WorkspaceNode", "build_graph"]
