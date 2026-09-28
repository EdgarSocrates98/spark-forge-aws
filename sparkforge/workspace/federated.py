"""Deterministic, bounded composition of local graph fragments.

Adapters provide explicit fragments.  The compositor unions only nodes and
edges that an adapter supplied; it never joins nodes by label or infers a
cross-fragment relationship.  Missing endpoints and source-side blind spots
remain named in ``unresolved``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

from sparkforge.workspace.freshness import FreshnessAssessment

GraphRecord = Mapping[str, Any]
GraphBuilder = Callable[..., "GraphFragment"]


@dataclass(frozen=True, slots=True)
class GraphFragment:
    """One explicitly sourced portion of a graph."""

    source: str = ""
    nodes: tuple[GraphRecord, ...] = ()
    edges: tuple[GraphRecord, ...] = ()
    provenance: tuple[GraphRecord, ...] = ()
    unresolved: tuple[GraphRecord, ...] = ()
    freshness: FreshnessAssessment = field(default_factory=FreshnessAssessment.unknown)
    source_id: str = ""
    source_kind: str = ""
    current_fingerprint: str | None = None
    indexed_fingerprint: str | None = None

    def __post_init__(self) -> None:
        for name in ("nodes", "edges", "provenance", "unresolved"):
            value = getattr(self, name)
            if value is None:
                value = ()
            elif isinstance(value, Mapping) or isinstance(value, str):
                value = (value,)
            else:
                value = tuple(value)
            object.__setattr__(self, name, value)
        if not isinstance(self.freshness, FreshnessAssessment):
            object.__setattr__(self, "freshness", _freshness_from_value(self.freshness))
        if not self.source and self.source_id:
            object.__setattr__(self, "source", self.source_id)
        if not self.source_id and self.source:
            object.__setattr__(self, "source_id", self.source)
        if self.current_fingerprint is not None or self.indexed_fingerprint is not None:
            object.__setattr__(
                self,
                "freshness",
                _freshness_from_mapping(
                    {
                        "current_fingerprint": self.current_fingerprint,
                        "indexed_fingerprint": self.indexed_fingerprint,
                    }
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "nodes": [dict(_record(item, kind="node")) for item in self.nodes],
            "edges": [dict(_record(item, kind="edge")) for item in self.edges],
            "provenance": [dict(_record(item, kind="provenance")) for item in self.provenance],
            "unresolved": [dict(_record(item, kind="unresolved")) for item in self.unresolved],
            "current_fingerprint": self.current_fingerprint,
            "indexed_fingerprint": self.indexed_fingerprint,
            "freshness": self.freshness.status,
        }


@dataclass(frozen=True, slots=True)
class GraphAdapter:
    """Named adapter around a deterministic fragment builder.

    ``builder`` may accept no argument or one source argument.  Existing
    adapter-like objects with an ``adapt`` method are also accepted by the
    compositor, so callers need not inherit this class.
    """

    name: str
    builder: GraphBuilder | None = None
    fragment: GraphFragment | None = None

    @property
    def source_id(self) -> str:
        return self.name

    def snapshot(self) -> GraphFragment:
        return self.adapt()

    def adapt(self, source: object | None = None) -> GraphFragment:
        if self.fragment is not None:
            return self.fragment
        if self.builder is None:
            if isinstance(source, GraphFragment):
                return source
            return fragment_from_graph(source, source=self.name)
        if source is None:
            result = self.builder()
        else:
            result = self.builder(source)
        return fragment_from_graph(result, source=self.name)


@dataclass(frozen=True, slots=True)
class FederatedGraph:
    """Bounded union of sourced graph evidence."""

    nodes: tuple[GraphRecord, ...] = ()
    edges: tuple[GraphRecord, ...] = ()
    provenance: tuple[GraphRecord, ...] = ()
    unresolved: tuple[GraphRecord, ...] = ()
    freshness: FreshnessAssessment = field(default_factory=FreshnessAssessment.unknown)
    sources: tuple[str, ...] = ()
    truncated: bool = False

    def neighbors(self, node_id: str, max_depth: int = 2) -> tuple[str, ...]:
        """Return bounded outbound neighbors from explicit edges only."""

        if max_depth < 0:
            return ()
        seen = {node_id}
        frontier = [node_id]
        for _ in range(max_depth):
            next_frontier: list[str] = []
            for edge in self.edges:
                source = _edge_value(edge, "source")
                target = _edge_value(edge, "target")
                if source == "" or target == "" or source not in frontier:
                    continue
                if target not in seen:
                    seen.add(target)
                    next_frontier.append(target)
            frontier = next_frontier
            if not frontier:
                break
        return tuple(sorted(seen - {node_id}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "nodes": [dict(item) for item in self.nodes],
            "edges": [dict(item) for item in self.edges],
            "provenance": [dict(item) for item in self.provenance],
            "unresolved": [dict(item) for item in self.unresolved],
            "freshness": self.freshness.status,
            "freshness_detail": self.freshness.to_dict(),
            "sources": list(self.sources),
            "truncated": self.truncated,
        }


def compose_federated_graph(
    fragments: Iterable[GraphFragment | GraphAdapter | object] | None = None,
    *,
    adapters: Iterable[GraphAdapter | object] | None = None,
    max_nodes: int = 10_000,
    max_edges: int = 20_000,
    max_provenance: int = 20_000,
    max_unresolved: int = 20_000,
) -> FederatedGraph:
    """Compose fragments deterministically under explicit resource bounds."""

    _require_positive("max_nodes", max_nodes)
    _require_positive("max_edges", max_edges)
    _require_positive("max_provenance", max_provenance)
    _require_positive("max_unresolved", max_unresolved)
    if fragments is not None and adapters is not None:
        raise ValueError("pass fragments or adapters, not both")

    inputs: Iterable[GraphFragment | GraphAdapter | object]
    if adapters is not None:
        inputs = adapters
    else:
        inputs = fragments or ()

    built = tuple(_resolve_input(item) for item in inputs)
    ordered = tuple(sorted(built, key=_fragment_key))
    sources = tuple(sorted({item.source for item in ordered if item.source}))
    freshness = _compose_freshness(item.freshness for item in ordered)

    unresolved: list[GraphRecord] = []
    provenance: list[GraphRecord] = []
    node_candidates: dict[str, list[GraphRecord]] = {}
    edge_candidates: dict[tuple[str, str, str], list[GraphRecord]] = {}

    for fragment in ordered:
        unresolved.extend(_records(fragment.unresolved, kind="unresolved"))
        provenance.extend(_records(fragment.provenance, kind="provenance"))
        for raw_node in fragment.nodes:
            node = _record(raw_node, kind="node")
            node_id = _node_value(node, "id")
            if not node_id:
                unresolved.append(_generated("graph_node_unresolved", fragment, node=node))
                continue
            node_candidates.setdefault(node_id, []).append(node)
        for raw_edge in fragment.edges:
            edge = _record(raw_edge, kind="edge")
            key = (
                _edge_value(edge, "source"),
                _edge_value(edge, "relation"),
                _edge_value(edge, "target"),
            )
            if not all(key):
                unresolved.append(_generated("graph_edge_unresolved", fragment, edge=edge))
                continue
            edge_candidates.setdefault(key, []).append(edge)

    nodes: list[GraphRecord] = []
    for node_id in sorted(node_candidates):
        candidates = sorted(node_candidates[node_id], key=_record_key)
        nodes.append(candidates[0])
        if len({_canonical(item) for item in candidates}) > 1:
            unresolved.append(
                {
                    "code": "graph_node_conflict",
                    "node_id": node_id,
                    "candidates": len(candidates),
                }
            )
    node_count = len(nodes)
    nodes, nodes_truncated = _bounded(nodes, max_nodes)
    if nodes_truncated:
        unresolved.append({"code": "graph_nodes_truncated", "omitted": node_count - len(nodes)})
    node_ids = {_node_value(item, "id") for item in nodes}

    edges: list[GraphRecord] = []
    for key in sorted(edge_candidates):
        candidates = sorted(edge_candidates[key], key=_record_key)
        edge = candidates[0]
        source, _relation, target = key
        if source not in node_ids or target not in node_ids:
            unresolved.append(
                {
                    "code": "graph_edge_unresolved",
                    "source": source,
                    "relation": key[1],
                    "target": target,
                }
            )
            continue
        edges.append(edge)
        if len({_canonical(item) for item in candidates}) > 1:
            unresolved.append(
                {
                    "code": "graph_edge_conflict",
                    "source": source,
                    "relation": key[1],
                    "target": target,
                    "candidates": len(candidates),
                }
            )
    edge_count = len(edges)
    edges, edges_truncated = _bounded(edges, max_edges)
    if edges_truncated:
        unresolved.append({"code": "graph_edges_truncated", "omitted": edge_count - len(edges)})
    provenance = _unique_records(provenance)
    provenance_count = len(provenance)
    provenance, provenance_truncated = _bounded(provenance, max_provenance)
    if provenance_truncated:
        unresolved.append(
            {"code": "graph_provenance_truncated", "omitted": provenance_count - len(provenance)}
        )
    unresolved, unresolved_truncated = _bounded_with_summary(
        _unique_records(unresolved), max_unresolved, "graph_unresolved_truncated"
    )

    return FederatedGraph(
        nodes=tuple(sorted(nodes, key=_record_key)),
        edges=tuple(sorted(edges, key=_record_key)),
        provenance=tuple(sorted(provenance, key=_record_key)),
        unresolved=tuple(sorted(unresolved, key=_record_key)),
        freshness=freshness,
        sources=sources,
        truncated=any(
            (nodes_truncated, edges_truncated, provenance_truncated, unresolved_truncated)
        ),
    )


def fragment_from_graph(graph: object, *, source: str = "") -> GraphFragment:
    """Adapt an existing workspace/semantic graph without deriving edges."""

    if isinstance(graph, GraphFragment):
        if source and not graph.source:
            return GraphFragment(
                source,
                graph.nodes,
                graph.edges,
                graph.provenance,
                graph.unresolved,
                graph.freshness,
                graph.source_id or source,
                graph.source_kind,
                graph.current_fingerprint,
                graph.indexed_fingerprint,
            )
        return graph
    if graph is None:
        return GraphFragment(source=source, unresolved=({"code": "graph_source_unresolved"},))

    payload: object = graph
    if isinstance(graph, Mapping) and isinstance(graph.get("graph"), Mapping):
        payload = graph["graph"]
    if isinstance(payload, Mapping):
        nodes = payload.get("nodes", ())
        edges = payload.get("edges", ())
        unresolved = graph.get("unresolved", ()) if isinstance(graph, Mapping) else ()
        provenance = graph.get("provenance", ()) if isinstance(graph, Mapping) else ()
        return GraphFragment(
            source=source or str(graph.get("source", "")),
            nodes=_sequence(nodes),
            edges=_sequence(edges),
            provenance=_sequence(provenance),
            unresolved=_sequence(unresolved),
            freshness=_freshness_from_mapping(graph),
            source_id=source or str(graph.get("source_id", graph.get("source", ""))),
            source_kind=str(graph.get("source_kind", "")),
            current_fingerprint=_optional_string(graph.get("current_fingerprint")),
            indexed_fingerprint=_optional_string(graph.get("indexed_fingerprint")),
        )

    nodes = getattr(graph, "nodes", ())
    edges = getattr(graph, "edges", ())
    unresolved = getattr(graph, "unresolved", ())
    provenance = getattr(graph, "provenance", ())
    return GraphFragment(
        source=source or str(getattr(graph, "source", "")),
        nodes=_sequence(nodes),
        edges=_sequence(edges),
        provenance=_sequence(provenance),
        unresolved=_sequence(unresolved),
        freshness=_freshness_from_value(getattr(graph, "freshness", None)),
        source_id=source or str(getattr(graph, "source_id", getattr(graph, "source", ""))),
        source_kind=str(getattr(graph, "source_kind", "")),
        current_fingerprint=_optional_string(getattr(graph, "current_fingerprint", None)),
        indexed_fingerprint=_optional_string(getattr(graph, "indexed_fingerprint", None)),
    )


# Public spellings for the compositor boundary.
compose = compose_federated_graph
compose_graph = compose_federated_graph
compositor = compose_federated_graph


def _resolve_input(item: GraphFragment | GraphAdapter | object) -> GraphFragment:
    if isinstance(item, GraphAdapter):
        return item.adapt()
    adapt = getattr(item, "adapt", None)
    if callable(adapt):
        return fragment_from_graph(adapt())
    snapshot = getattr(item, "snapshot", None)
    if callable(snapshot):
        return fragment_from_graph(snapshot())
    if callable(item) and not isinstance(item, (str, bytes)):
        return fragment_from_graph(item())
    return fragment_from_graph(item)


def _compose_freshness(values: Iterable[FreshnessAssessment]) -> FreshnessAssessment:
    assessments = tuple(values)
    statuses = {item.status for item in assessments}
    if "stale" in statuses:
        return FreshnessAssessment("stale", reason="fragment_stale")
    if assessments and statuses == {"fresh"}:
        return FreshnessAssessment("fresh", reason="all_fragments_fresh")
    return FreshnessAssessment.unknown(
        "fragment_freshness_unresolved" if assessments else "no_fragments"
    )


def _freshness_from_mapping(value: Mapping[str, Any]) -> FreshnessAssessment:
    current = value.get("current_fingerprint")
    indexed = value.get("indexed_fingerprint")
    if current is not None or indexed is not None:
        from sparkforge.workspace.freshness import assess_freshness

        return assess_freshness(current, indexed)
    return _freshness_from_value(value.get("freshness"))


def _freshness_from_value(value: object) -> FreshnessAssessment:
    if isinstance(value, FreshnessAssessment):
        return value
    if isinstance(value, Mapping):
        status = value.get("freshness", value.get("status"))
        if status in {"fresh", "stale", "unknown"}:
            return FreshnessAssessment(
                status,  # type: ignore[arg-type]
                _optional_string(value.get("current_fingerprint")),
                _optional_string(value.get("indexed_fingerprint")),
                str(value.get("reason") or "provided_status"),
            )
    if value in {"fresh", "stale", "unknown"}:
        return FreshnessAssessment(value, reason="provided_status")  # type: ignore[arg-type]
    return FreshnessAssessment.unknown()


def _records(values: Iterable[object], *, kind: str) -> list[GraphRecord]:
    result: list[GraphRecord] = []
    for value in values:
        if isinstance(value, Mapping):
            result.append(dict(value))
        elif is_dataclass(value):
            result.append(
                {
                    item.name: getattr(value, item.name)
                    for item in fields(value)
                }
            )
        elif kind == "node" and isinstance(value, str):
            result.append({"id": value})
        else:
            result.append({"value": value})
    return result


def _record(value: object, *, kind: str) -> GraphRecord:
    return _records((value,), kind=kind)[0]


def _sequence(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping) or isinstance(value, str):
        return (value,)
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError:
        return (value,)


def _generated(code: str, fragment: GraphFragment, **details: object) -> GraphRecord:
    return {"code": code, **details, **({"source": fragment.source} if fragment.source else {})}


def _node_value(node: GraphRecord, key: str) -> str:
    value = node.get(key)
    return value.strip() if isinstance(value, str) else ""


def _edge_value(edge: GraphRecord, key: str) -> str:
    return _node_value(edge, key)


def _optional_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _fragment_key(fragment: GraphFragment) -> tuple[str, str]:
    return fragment.source, _canonical(
        {
            "nodes": [_record(item, kind="node") for item in fragment.nodes],
            "edges": [_record(item, kind="edge") for item in fragment.edges],
            "unresolved": [_record(item, kind="unresolved") for item in fragment.unresolved],
        }
    )


def _record_key(value: GraphRecord) -> str:
    return _canonical(value)


def _canonical(value: object) -> str:
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if is_dataclass(value):
        return {item.name: _json_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _unique_records(values: Sequence[GraphRecord]) -> list[GraphRecord]:
    unique: dict[str, GraphRecord] = {}
    for value in values:
        unique.setdefault(_canonical(value), value)
    return list(unique.values())


def _bounded(values: Sequence[GraphRecord], limit: int) -> tuple[list[GraphRecord], bool]:
    ordered = sorted(values, key=_record_key)
    if len(ordered) <= limit:
        return ordered, False
    return ordered[:limit], True


def _bounded_with_summary(
    values: Sequence[GraphRecord], limit: int, code: str
) -> tuple[list[GraphRecord], bool]:
    ordered = sorted(values, key=_record_key)
    if len(ordered) <= limit:
        return ordered, False
    summary = {"code": code, "omitted": len(ordered) - limit}
    if limit == 1:
        return [summary], True
    return [*ordered[: limit - 1], summary], True


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


__all__ = [
    "FederatedGraph",
    "GraphAdapter",
    "GraphFragment",
    "compose",
    "compose_federated_graph",
    "compose_graph",
    "compositor",
    "fragment_from_graph",
]
