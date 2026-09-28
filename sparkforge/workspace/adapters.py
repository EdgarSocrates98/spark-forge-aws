"""Explicit source adapters for offline federated workspace graphs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any, Protocol

from sparkforge.workspace.federated import GraphFragment, fragment_from_graph


class FragmentAdapter(Protocol):
    source_kind: str

    def adapt(self, source: object) -> GraphFragment:
        ...


def semantic_graph_fragment(graph: object, source_id: str) -> GraphFragment:
    return _adapt(graph, source_id, "semantic")


def artifact_graph_fragment(payload: Mapping[str, object], source_id: str) -> GraphFragment:
    return _adapt(payload, source_id, "aws_artifact")


def transcript_evidence_fragment(
    payload: Mapping[str, object], source_id: str
) -> GraphFragment:
    return _adapt(payload, source_id, "provider_transcript")


def _adapt(source: object, source_id: str, source_kind: str) -> GraphFragment:
    normalized_source_id = _source_id(source_id)
    fragment = fragment_from_graph(source, source=normalized_source_id)
    return GraphFragment(
        source=normalized_source_id,
        nodes=tuple(_record(item) for item in fragment.nodes),
        edges=tuple(_record(item) for item in fragment.edges),
        provenance=tuple(_record(item) for item in fragment.provenance),
        unresolved=tuple(_record(item) for item in fragment.unresolved),
        freshness=fragment.freshness,
        source_id=normalized_source_id,
        source_kind=source_kind,
        current_fingerprint=fragment.current_fingerprint,
        indexed_fingerprint=fragment.indexed_fingerprint,
    )


def _record(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {item.name: getattr(value, item.name) for item in fields(value)}
    return {"value": value}


def _source_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("source_id must be non-empty")
    return value.strip()


__all__ = [
    "FragmentAdapter",
    "artifact_graph_fragment",
    "semantic_graph_fragment",
    "transcript_evidence_fragment",
]
