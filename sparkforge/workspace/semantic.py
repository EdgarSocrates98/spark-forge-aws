"""Bounded semantic graph over declared repositories and local Code Intelligence.

This module composes existing repository relationships and already-indexed
symbols/data-flow rows. It never executes repository code and never guesses a
dynamic dataset name; unresolved rows remain explicit graph evidence.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.codeintel.db import BANCO_PADRAO
from sparkforge.paths import resolve_within
from sparkforge.workspace.freshness import FreshnessAssessment
from sparkforge.workspace.manifest import WorkspaceManifest


@dataclass(frozen=True, slots=True)
class SemanticNode:
    id: str
    kind: str
    label: str
    repository: str


@dataclass(frozen=True, slots=True)
class SemanticEdge:
    source: str
    relation: str
    target: str
    repository: str
    line: int | None = None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class SemanticGraph:
    nodes: tuple[SemanticNode, ...]
    edges: tuple[SemanticEdge, ...]
    unresolved: tuple[dict[str, str], ...]
    manifest_fingerprint: str
    freshness: FreshnessAssessment = field(default_factory=FreshnessAssessment.unknown)

    def impact(
        self,
        node_id: str,
        *,
        direction: str = "both",
        max_depth: int = 2,
    ) -> tuple[str, ...]:
        """Return bounded transitive impact for one semantic node."""
        if direction not in {"inbound", "outbound", "both"}:
            raise ValueError("direction must be inbound, outbound or both")
        if max_depth < 0:
            return ()
        seen = {node_id}
        frontier = [node_id]
        for _ in range(max_depth):
            next_frontier: list[str] = []
            for edge in self.edges:
                follows = (
                    (direction in {"outbound", "both"} and edge.source in frontier)
                    or (direction in {"inbound", "both"} and edge.target in frontier)
                )
                if not follows:
                    continue
                candidate = edge.target if edge.source in frontier else edge.source
                if candidate not in seen:
                    seen.add(candidate)
                    next_frontier.append(candidate)
            frontier = next_frontier
            if not frontier:
                break
        return tuple(sorted(seen - {node_id}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "nodes": [
                {
                    "id": item.id,
                    "kind": item.kind,
                    "label": item.label,
                    "repository": item.repository,
                }
                for item in self.nodes
            ],
            "edges": [
                {
                    "source": item.source,
                    "relation": item.relation,
                    "target": item.target,
                    "repository": item.repository,
                    "line": item.line,
                    "confidence": item.confidence,
                }
                for item in self.edges
            ],
            "unresolved": list(self.unresolved),
            "manifest_fingerprint": self.manifest_fingerprint,
            "freshness": self.freshness.status,
            "freshness_detail": self.freshness.to_dict(),
        }


def build_semantic_graph(
    manifest: WorkspaceManifest,
    *,
    databases: Mapping[str, str | Path] | None = None,
    max_nodes: int = 10_000,
    freshness: FreshnessAssessment | None = None,
) -> SemanticGraph:
    """Compose declared workspace and indexed code/data-flow relationships."""
    if max_nodes <= 0:
        raise ValueError("max_nodes must be positive")
    nodes: dict[str, SemanticNode] = {}
    edges: list[SemanticEdge] = []
    unresolved: list[dict[str, str]] = []

    def add_node(node: SemanticNode) -> bool:
        if node.id in nodes:
            return True
        if len(nodes) >= max_nodes:
            unresolved.append(
                {"code": "semantic_graph_truncated", "repository": node.repository}
            )
            return False
        nodes[node.id] = node
        return True

    for repository in manifest.repositories:
        repo_id = f"repo:{repository.name}"
        add_node(SemanticNode(repo_id, "repository", repository.name, repository.name))

    for relationship in manifest.relationships:
        source = f"repo:{relationship.source}"
        target = f"repo:{relationship.target}"
        if target not in nodes:
            unresolved.append(
                {
                    "code": "workspace_repository_unresolved",
                    "source": relationship.source,
                    "target": relationship.target,
                }
            )
            continue
        edges.append(SemanticEdge(source, relationship.relation, target, relationship.source))

    for repository in manifest.repositories:
        database = (databases or {}).get(repository.name)
        if database is None:
            database = repository.path / BANCO_PADRAO
        database_path = resolve_within(repository.path, database)
        if database_path is None or not database_path.is_file():
            unresolved.append(
                {
                    "code": "codeintel_index_unavailable",
                    "repository": repository.name,
                }
            )
            continue
        try:
            _add_index(
                repository.name,
                database_path,
                add_node,
                nodes,
                edges,
                unresolved,
            )
        except sqlite3.DatabaseError as exc:
            unresolved.append(
                {
                    "code": "codeintel_index_unreadable",
                    "repository": repository.name,
                    "detail": str(exc),
                }
            )

    return SemanticGraph(
        tuple(sorted(nodes.values(), key=lambda item: item.id)),
        tuple(
            sorted(
                edges,
                key=lambda item: (
                    item.source,
                    item.relation,
                    item.target,
                    item.line or 0,
                ),
            )
        ),
        tuple(sorted(unresolved, key=lambda item: (item.get("repository", ""), item["code"]))),
        _manifest_fingerprint(manifest),
        freshness or FreshnessAssessment.unknown("codeintel_freshness_not_assessed"),
    )


def _add_index(
    repository: str,
    database: Path,
    add_node: Any,
    nodes: dict[str, SemanticNode],
    edges: list[SemanticEdge],
    unresolved: list[dict[str, str]],
) -> None:
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        files = {
            str(_file_id): str(path)
            for _file_id, path in connection.execute("SELECT id, path FROM files ORDER BY path")
        }
        for _file_id, path in files.items():
            file_node = f"{repository}:file:{path}"
            if add_node(SemanticNode(file_node, "file", path, repository)):
                edges.append(SemanticEdge(f"repo:{repository}", "contains", file_node, repository))

        symbol_ids: set[str] = set()
        for node_id, file_id, _kind, _name, qualified_name, line in connection.execute(
            "SELECT id, file_id, kind, name, qualified_name, start_line "
            "FROM nodes ORDER BY id"
        ):
            file_path = files.get(str(file_id))
            if file_path is None:
                unresolved.append({"code": "codeintel_file_missing", "repository": repository})
                continue
            symbol_node = f"{repository}:symbol:{node_id}"
            if not add_node(SemanticNode(symbol_node, "symbol", str(qualified_name), repository)):
                continue
            symbol_ids.add(str(node_id))
            edges.append(
                SemanticEdge(
                    f"{repository}:file:{file_path}",
                    "defines",
                    symbol_node,
                    repository,
                    int(line),
                )
            )

        for source_id, target_id, kind, line, confidence in connection.execute(
            "SELECT source_id, target_id, kind, line, confidence FROM edges "
            "ORDER BY source_id, target_id, line"
        ):
            if str(source_id) in symbol_ids and str(target_id) in symbol_ids:
                edges.append(
                    SemanticEdge(
                        f"{repository}:symbol:{source_id}",
                        str(kind),
                        f"{repository}:symbol:{target_id}",
                        repository,
                        int(line),
                        float(confidence),
                    )
                )

        for row in connection.execute(
            "SELECT file_id, source_name, source_kind, source_resolved, "
            "target_name, target_kind, target_resolved, operation, line, confidence "
            "FROM data_flow ORDER BY file_id, line, id"
        ):
            (
                file_id,
                source_name,
                source_kind,
                source_resolved,
                target_name,
                target_kind,
                target_resolved,
                operation,
                line,
                confidence,
            ) = row
            if not source_resolved or not target_resolved:
                unresolved.append(
                    {
                        "code": "data_flow_unresolved",
                        "repository": repository,
                        "operation": str(operation),
                    }
                )
                continue
            source = _data_node(repository, str(source_kind), str(source_name))
            target = _data_node(repository, str(target_kind), str(target_name))
            if not add_node(SemanticNode(source[0], source[1], source[2], repository)):
                continue
            if not add_node(SemanticNode(target[0], target[1], target[2], repository)):
                continue
            file_path = files.get(str(file_id))
            if file_path is not None:
                edges.append(
                    SemanticEdge(
                        f"{repository}:file:{file_path}",
                        "observes",
                        source[0],
                        repository,
                        int(line),
                        float(confidence),
                    )
                )
            edges.append(
                SemanticEdge(
                    source[0],
                    str(operation),
                    target[0],
                    repository,
                    int(line),
                    float(confidence),
                )
            )
    finally:
        connection.close()


def _data_node(repository: str, kind: str, name: str) -> tuple[str, str, str]:
    normalized_kind = "dataset" if kind in {"dataset", "table", "path", "sql"} else "dataframe"
    node_id = f"{repository}:data:{normalized_kind}:{name}"
    return node_id, normalized_kind, name


def _manifest_fingerprint(manifest: WorkspaceManifest) -> str:
    import hashlib
    import json

    payload = {
        "name": manifest.name,
        "repositories": [
            (item.name, item.fingerprint, item.exists) for item in manifest.repositories
        ],
        "relationships": [
            (item.source, item.relation, item.target) for item in manifest.relationships
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = ["SemanticEdge", "SemanticGraph", "SemanticNode", "build_semantic_graph"]
