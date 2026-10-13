"""Offline metadata graph, lineage and blast-radius analysis.

The module accepts only declared nodes and edges. It never discovers a service,
joins by label, calls a provider or turns a missing endpoint into an inferred
relationship. Every blind spot remains in ``unresolved``.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PLATFORM_NODE_KINDS = frozenset(
    {
        "dataset",
        "job",
        "run",
        "consumer",
        "producer",
        "contract",
        "owner",
        "slo",
        "dependency",
        "schema",
        "dashboard",
        "metric",
        "model",
        "service",
        "topic",
        "stream",
        "table",
        "catalog",
        "orchestrator",
        "feature",
        "vector_index",
    }
)
_DIRECTIONS = frozenset({"downstream", "upstream", "both"})
_STATES = frozenset({"declared", "observed", "inferred", "unresolved"})


class PlatformGraphError(ValueError):
    """Invalid or unsafe platform graph declaration."""


@dataclass(frozen=True, slots=True)
class PlatformNode:
    """One platform entity with explicit evidence and declared state."""

    id: str
    kind: str
    name: str
    subtype: str = ""
    attrs: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[Mapping[str, Any], ...] = ()
    state: str = "declared"
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "subtype": self.subtype,
            "attrs": _json_value(self.attrs),
            "evidence": [_json_value(item) for item in self.evidence],
            "state": self.state,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class PlatformEdge:
    """One explicit directed dependency or lineage relation."""

    source: str
    relation: str
    target: str
    evidence: tuple[Mapping[str, Any], ...] = ()
    attrs: Mapping[str, Any] = field(default_factory=dict)
    state: str = "declared"
    source_system: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "evidence": [_json_value(item) for item in self.evidence],
            "attrs": _json_value(self.attrs),
            "state": self.state,
            "source_system": self.source_system,
        }


@dataclass(frozen=True, slots=True)
class PlatformImpact:
    """Bounded impact projection for one changed entity or attribute."""

    root: str
    direction: str
    max_depth: int
    changed_attribute: str | None
    direct: tuple[str, ...]
    transitive: tuple[str, ...]
    affected: tuple[str, ...]
    paths: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "direction": self.direction,
            "max_depth": self.max_depth,
            "changed_attribute": self.changed_attribute,
            "direct": list(self.direct),
            "transitive": list(self.transitive),
            "affected": list(self.affected),
            "paths": [_json_value(item) for item in self.paths],
            "unresolved": [_json_value(item) for item in self.unresolved],
        }


@dataclass(frozen=True, slots=True)
class PlatformGraph:
    """Canonical graph composed from one or more declared manifests."""

    platform: str
    schema_version: int
    nodes: tuple[PlatformNode, ...]
    edges: tuple[PlatformEdge, ...]
    provenance: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def impact(
        self,
        node_id: str,
        *,
        direction: str = "downstream",
        max_depth: int = 3,
        max_items: int = 500,
        changed_attribute: str | None = None,
    ) -> PlatformImpact:
        """Walk explicit edges and return a deterministic bounded blast radius."""
        if direction not in _DIRECTIONS:
            raise ValueError("direction must be downstream, upstream or both")
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        if max_items <= 0:
            raise ValueError("max_items must be positive")

        nodes = {item.id: item for item in self.nodes}
        unresolved = [dict(item) for item in self.unresolved]
        root = nodes.get(node_id)
        if root is None:
            unresolved.append({"code": "platform_impact_node_unresolved", "node_id": node_id})
        elif changed_attribute and not _contains_attribute(root.attrs, changed_attribute):
            unresolved.append(
                {
                    "code": "platform_impact_attribute_unresolved",
                    "node_id": node_id,
                    "attribute": changed_attribute,
                }
            )

        adjacency = _adjacency(self.edges, direction)
        queue: deque[tuple[str, int, tuple[str, ...], tuple[Mapping[str, Any], ...]]] = deque(
            [(node_id, 0, (node_id,), ())]
        )
        seen = {node_id}
        discovered: list[tuple[str, int, tuple[str, ...], tuple[Mapping[str, Any], ...]]] = []
        while queue and len(discovered) < max_items:
            current, depth, path, relations = queue.popleft()
            if depth >= max_depth:
                continue
            for candidate, relation in adjacency.get(current, ()):
                if candidate in seen:
                    continue
                seen.add(candidate)
                next_path = (*path, candidate)
                next_relations = (
                    *relations,
                    {"source": current, "relation": relation, "target": candidate},
                )
                discovered.append((candidate, depth + 1, next_path, next_relations))
                queue.append((candidate, depth + 1, next_path, next_relations))

        if queue:
            unresolved.append(
                {
                    "code": "platform_impact_truncated",
                    "max_items": max_items,
                    "omitted_frontier": len(queue),
                }
            )

        direct = tuple(
            sorted(candidate for candidate, depth, _path, _relations in discovered if depth == 1)
        )
        transitive = tuple(
            sorted(candidate for candidate, depth, _path, _relations in discovered if depth > 1)
        )
        paths = tuple(
            {
                "node_id": candidate,
                "depth": depth,
                "nodes": list(path),
                "edges": [_json_value(item) for item in relations],
            }
            for candidate, depth, path, relations in sorted(
                discovered, key=lambda item: (item[1], item[0], item[2])
            )
        )
        return PlatformImpact(
            root=node_id,
            direction=direction,
            max_depth=max_depth,
            changed_attribute=changed_attribute,
            direct=direct,
            transitive=transitive,
            affected=tuple(sorted(candidate for candidate, *_rest in discovered)),
            paths=paths,
            unresolved=tuple(_unique_sorted(unresolved)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "platform": self.platform,
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "provenance": [_json_value(item) for item in self.provenance],
            "unresolved": [_json_value(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_platform_graph(path: str | Path) -> PlatformGraph:
    """Load one JSON/YAML graph manifest without contacting external systems."""
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise PlatformGraphError(f"platform graph manifest not found: {path}")
    try:
        raw = (
            json.loads(target.read_text(encoding="utf-8"))
            if target.suffix.lower() == ".json"
            else yaml.safe_load(target.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise PlatformGraphError(f"platform graph manifest unreadable: {path}") from exc
    return _build_graph(raw, source=target.as_posix())


def analyze_platform_graph(
    path: str | Path,
    *,
    changed_node: str | None = None,
    changed_attribute: str | None = None,
    direction: str = "downstream",
    max_depth: int = 3,
    max_items: int = 500,
) -> dict[str, Any]:
    """Return graph and optional impact projection in one stable envelope."""
    graph = load_platform_graph(path)
    result = {"graph": graph.to_dict(), "impact": None}
    if changed_node is not None:
        result["impact"] = graph.impact(
            changed_node,
            direction=direction,
            max_depth=max_depth,
            max_items=max_items,
            changed_attribute=changed_attribute,
        ).to_dict()
    return result


def _build_graph(raw: object, *, source: str) -> PlatformGraph:
    if not isinstance(raw, Mapping):
        raise PlatformGraphError("platform graph root must be an object")
    if raw.get("schema_version", 1) != 1:
        raise PlatformGraphError("platform graph schema_version must be 1")
    platform = _required_string(raw.get("platform", raw.get("workspace")), "platform")
    nodes_raw = raw.get("nodes", [])
    edges_raw = raw.get("edges", [])
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
        raise PlatformGraphError("platform graph nodes and edges must be lists")

    unresolved = _record_list(raw.get("unresolved", []), "unresolved")
    provenance = _record_list(raw.get("provenance", [{"source": source}]), "provenance")
    node_candidates: dict[str, list[PlatformNode]] = {}
    for raw_node in nodes_raw:
        node = _parse_node(raw_node)
        node_candidates.setdefault(node.id, []).append(node)
    nodes: list[PlatformNode] = []
    for node_id in sorted(node_candidates):
        candidates = sorted(node_candidates[node_id], key=lambda item: _canonical(item.to_dict()))
        nodes.append(candidates[0])
        if len({_canonical(item.to_dict()) for item in candidates}) > 1:
            unresolved.append(
                {
                    "code": "platform_node_conflict",
                    "node_id": node_id,
                    "candidates": len(candidates),
                }
            )

    edge_candidates: dict[tuple[str, str, str], list[PlatformEdge]] = {}
    for raw_edge in edges_raw:
        edge = _parse_edge(raw_edge)
        edge_candidates.setdefault((edge.source, edge.relation, edge.target), []).append(edge)
    node_ids = {item.id for item in nodes}
    edges: list[PlatformEdge] = []
    for key in sorted(edge_candidates):
        candidates = sorted(edge_candidates[key], key=lambda item: _canonical(item.to_dict()))
        edge = candidates[0]
        if edge.source not in node_ids or edge.target not in node_ids:
            unresolved.append(
                {
                    "code": "platform_edge_unresolved",
                    **dict(zip(("source", "relation", "target"), key, strict=True)),
                }
            )
            continue
        edges.append(edge)
        if len({_canonical(item.to_dict()) for item in candidates}) > 1:
            unresolved.append(
                {
                    "code": "platform_edge_conflict",
                    **dict(zip(("source", "relation", "target"), key, strict=True)),
                    "candidates": len(candidates),
                }
            )

    payload = {
        "schema_version": 1,
        "platform": platform,
        "nodes": [item.to_dict() for item in nodes],
        "edges": [item.to_dict() for item in edges],
        "provenance": [_json_value(item) for item in provenance],
        "unresolved": [_json_value(item) for item in _unique_sorted(unresolved)],
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return PlatformGraph(
        platform=platform,
        schema_version=1,
        nodes=tuple(nodes),
        edges=tuple(edges),
        provenance=tuple(provenance),
        unresolved=tuple(_unique_sorted(unresolved)),
        fingerprint=fingerprint,
    )


def _parse_node(raw: object) -> PlatformNode:
    if not isinstance(raw, Mapping):
        raise PlatformGraphError("platform node must be an object")
    node_id = _required_string(raw.get("id"), "node.id")
    kind = _required_string(raw.get("kind", raw.get("type")), f"node[{node_id}].kind")
    if kind not in PLATFORM_NODE_KINDS:
        raise PlatformGraphError(f"node[{node_id}].kind unsupported: {kind}")
    state = str(raw.get("state", "declared"))
    if state not in _STATES:
        raise PlatformGraphError(f"node[{node_id}].state unsupported: {state}")
    attrs = raw.get("attrs", {})
    if not isinstance(attrs, Mapping):
        raise PlatformGraphError(f"node[{node_id}].attrs must be an object")
    return PlatformNode(
        id=node_id,
        kind=kind,
        name=str(raw.get("name", node_id)),
        subtype=str(raw.get("subtype", "")),
        attrs=dict(attrs),
        evidence=_evidence(raw.get("evidence", []), f"node[{node_id}].evidence"),
        state=state,
        source=str(raw.get("source", "")),
    )


def _parse_edge(raw: object) -> PlatformEdge:
    if not isinstance(raw, Mapping):
        raise PlatformGraphError("platform edge must be an object")
    source = _required_string(raw.get("source"), "edge.source")
    relation = _required_string(raw.get("relation"), f"edge[{source}].relation")
    target = _required_string(raw.get("target"), f"edge[{source}].target")
    state = str(raw.get("state", "declared"))
    if state not in _STATES:
        raise PlatformGraphError(f"edge[{source}->{target}].state unsupported: {state}")
    attrs = raw.get("attrs", {})
    if not isinstance(attrs, Mapping):
        raise PlatformGraphError(f"edge[{source}->{target}].attrs must be an object")
    return PlatformEdge(
        source=source,
        relation=relation,
        target=target,
        evidence=_evidence(raw.get("evidence", []), f"edge[{source}->{target}].evidence"),
        attrs=dict(attrs),
        state=state,
        source_system=str(raw.get("source_system", "")),
    )


def _evidence(value: object, field_name: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise PlatformGraphError(f"{field_name} must be a list")
    result: list[Mapping[str, Any]] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append({"ref": item.strip()})
        elif isinstance(item, Mapping):
            result.append(dict(item))
        else:
            raise PlatformGraphError(f"{field_name} contains invalid evidence")
    return tuple(result)


def _record_list(value: object, field_name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise PlatformGraphError(f"{field_name} must be a list of objects")
    return [dict(item) for item in value]


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlatformGraphError(f"{field_name} must be a non-empty string")
    return value.strip()


def _adjacency(
    edges: Sequence[PlatformEdge], direction: str
) -> dict[str, tuple[tuple[str, str], ...]]:
    values: dict[str, list[tuple[str, str]]] = {}
    for edge in edges:
        if direction in {"downstream", "both"}:
            values.setdefault(edge.source, []).append((edge.target, edge.relation))
        if direction in {"upstream", "both"}:
            values.setdefault(edge.target, []).append((edge.source, edge.relation))
    return {key: tuple(sorted(value)) for key, value in values.items()}


def _contains_attribute(attrs: Mapping[str, Any], path: str) -> bool:
    current: Any = attrs
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False
        current = current[part]
    return True


def _unique_sorted(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(item): dict(item) for item in values}
    return [unique[key] for key in sorted(unique)]


def _canonical(value: object) -> str:
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


__all__ = [
    "PLATFORM_NODE_KINDS",
    "PlatformEdge",
    "PlatformGraph",
    "PlatformGraphError",
    "PlatformImpact",
    "PlatformNode",
    "analyze_platform_graph",
    "load_platform_graph",
]
