"""Composição declarativa de um pipeline streaming sobre Facts existentes.

O contrato é uma declaração de identidade, não uma topologia descoberta. Cada
node usa ``kind`` e atributos escalares exatos para localizar um único Fact;
zero ou múltiplos matches permanecem unresolved. Edges só são verified quando
os dois endpoints foram observados sem ambiguidade.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge_aws.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_pipeline@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "streaming.pipeline.node",
        "streaming.pipeline.link",
        "streaming.pipeline",
        "streaming.pipeline.unresolved",
    }
)

_SCALAR = (str, int, float, bool)


def _subject(symbol: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": "<streaming-pipeline>",
        "line": 0,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(facts: Sequence[Fact]) -> dict[str, Any]:
    return {
        "artifact": "<streaming-pipeline>",
        "artifacts": sorted(
            {
                str(fact.provenance.get("artifact", ""))
                for fact in facts
                if fact.provenance.get("artifact")
            }
        ),
        "extractor": EXTRACTOR_ID,
    }


def _fact(
    kind: str,
    pipeline_id: str,
    *,
    symbol: str | None = None,
    attrs: dict[str, Any] | None = None,
    measures: dict[str, Any] | None = None,
    facts: Sequence[Fact] = (),
) -> Fact:
    return Fact(
        kind=kind,
        subject=_subject(symbol or f"{pipeline_id}:{kind}"),
        attrs=attrs or {},
        measures=measures or {},
        provenance=_provenance(facts),
    )


def _unresolved(
    pipeline_id: str,
    reason: str,
    *,
    facts: Sequence[Fact] = (),
    **attrs: Any,
) -> Fact:
    identity = attrs.get("node_id") or attrs.get("edge_id") or attrs.get("selector_kind")
    return _fact(
        "streaming.pipeline.unresolved",
        pipeline_id or "<invalid>",
        symbol=f"{pipeline_id or '<invalid>'}:unresolved:{reason}:{identity or 'contract'}",
        attrs={"pipeline_id": pipeline_id or None, "reason": reason, **attrs},
        facts=facts,
    )


def _is_scalar(value: Any) -> bool:
    return isinstance(value, _SCALAR) and not isinstance(value, (list, dict))


def _contract_error(contract: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(contract, Mapping):
        return "contract_must_be_object", {}
    if contract.get("schema_version") != 1:
        return "unsupported_schema_version", {"schema_version": contract.get("schema_version")}
    pipeline_id = contract.get("pipeline_id")
    if not isinstance(pipeline_id, str) or not pipeline_id.strip():
        return "pipeline_id_missing", {}
    nodes = contract.get("nodes")
    edges = contract.get("edges")
    if not isinstance(nodes, list) or not nodes:
        return "nodes_must_be_non_empty_list", {}
    if not isinstance(edges, list):
        return "edges_must_be_list", {}
    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, Mapping):
            return "node_must_be_object", {}
        node_id = node.get("id")
        selector = node.get("selector")
        if not isinstance(node_id, str) or not node_id.strip():
            return "node_id_missing", {}
        if node_id in node_ids:
            return "node_id_duplicate", {"node_id": node_id}
        node_ids.add(node_id)
        if not isinstance(selector, Mapping):
            return "selector_must_be_object", {"node_id": node_id}
        kind = selector.get("kind")
        attrs = selector.get("attrs", {})
        if not isinstance(kind, str) or not kind.strip():
            return "selector_kind_missing", {"node_id": node_id}
        if not isinstance(attrs, Mapping):
            return "selector_attrs_must_be_object", {"node_id": node_id}
        if any(not isinstance(key, str) or not key.strip() for key in attrs):
            return "selector_attr_key_invalid", {"node_id": node_id}
        if any(not _is_scalar(value) for value in attrs.values()):
            return "selector_attr_value_not_scalar", {"node_id": node_id}
    edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, Mapping):
            return "edge_must_be_object", {}
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id.strip():
            return "edge_id_missing", {}
        if edge_id in edge_ids:
            return "edge_id_duplicate", {"edge_id": edge_id}
        edge_ids.add(edge_id)
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            return "edge_endpoint_unknown", {"edge_id": edge_id}
    return None


def build_streaming_pipeline(
    facts: Sequence[Fact], contract: Mapping[str, Any] | None
) -> list[Fact]:
    """Compose a declared pipeline without guessing topology or identity."""
    source_facts = list({fact.id: fact for fact in facts}.values())
    error = _contract_error(contract)
    if error is not None:
        reason, attrs = error
        pipeline_id = contract.get("pipeline_id", "") if isinstance(contract, Mapping) else ""
        return [_unresolved(str(pipeline_id), reason, facts=source_facts, **attrs)]

    assert isinstance(contract, Mapping)
    pipeline_id = str(contract["pipeline_id"]).strip()
    nodes = contract["nodes"]
    edges = contract["edges"]
    node_status: dict[str, str] = {}
    node_source: dict[str, Fact] = {}
    output: list[Fact] = []

    for node in nodes:
        node_id = str(node["id"])
        selector = node["selector"]
        selector_kind = str(selector["kind"])
        selector_attrs = dict(selector.get("attrs", {}))
        matches = [
            fact
            for fact in source_facts
            if fact.kind == selector_kind
            and all((fact.attrs or {}).get(key) == value for key, value in selector_attrs.items())
        ]
        if len(matches) == 1:
            node_status[node_id] = "verified"
            node_source[node_id] = matches[0]
            output.append(
                _fact(
                    "streaming.pipeline.node",
                    pipeline_id,
                    symbol=f"{pipeline_id}:node:{node_id}",
                    attrs={
                        "pipeline_id": pipeline_id,
                        "node_id": node_id,
                        "status": "verified",
                        "selector_kind": selector_kind,
                        "selector_attrs": selector_attrs,
                        "source_fact_ids": [matches[0].id],
                        "causal_inference": False,
                    },
                    measures={"match_count": 1},
                    facts=[matches[0]],
                )
            )
            continue

        reason = "selector_not_found" if not matches else "selector_ambiguous"
        node_status[node_id] = "unresolved"
        output.append(
            _fact(
                "streaming.pipeline.node",
                pipeline_id,
                attrs={
                    "pipeline_id": pipeline_id,
                    "node_id": node_id,
                    "status": "unresolved",
                    "selector_kind": selector_kind,
                    "selector_attrs": selector_attrs,
                    "source_fact_ids": [],
                    "causal_inference": False,
                },
                measures={"match_count": len(matches)},
                facts=matches,
            )
        )
        output.append(
            _unresolved(
                pipeline_id,
                reason,
                facts=matches or source_facts,
                node_id=node_id,
                selector_kind=selector_kind,
                selector_attrs=selector_attrs,
                match_count=len(matches),
            )
        )

    verified_edges = 0
    source_fact_ids: set[str] = set()
    for source in node_source.values():
        source_fact_ids.add(source.id)
    for edge in edges:
        edge_id = str(edge["id"])
        source_id = str(edge["from"])
        target_id = str(edge["to"])
        if node_status[source_id] == "verified" and node_status[target_id] == "verified":
            verified_edges += 1
            edge_facts = [node_source[source_id], node_source[target_id]]
            output.append(
                _fact(
                    "streaming.pipeline.link",
                    pipeline_id,
                    symbol=f"{pipeline_id}:edge:{edge_id}",
                    attrs={
                        "pipeline_id": pipeline_id,
                        "edge_id": edge_id,
                        "from_node": source_id,
                        "to_node": target_id,
                        "status": "verified",
                        "source_fact_ids": sorted({fact.id for fact in edge_facts}),
                        "causal_inference": False,
                    },
                    measures={"endpoint_count": 2},
                    facts=edge_facts,
                )
            )
        else:
            output.append(
                _unresolved(
                    pipeline_id,
                    "edge_endpoint_unresolved",
                    facts=source_facts,
                    edge_id=edge_id,
                    from_node=source_id,
                    to_node=target_id,
                    unresolved_endpoints=sorted(
                        node_id
                        for node_id in (source_id, target_id)
                        if node_status[node_id] != "verified"
                    ),
                )
            )

    unresolved_count = sum(
        fact.kind == "streaming.pipeline.unresolved" for fact in output
    )
    status = "verified" if unresolved_count == 0 and verified_edges == len(edges) else "unresolved"
    output.append(
        _fact(
            "streaming.pipeline",
            pipeline_id,
            symbol=f"{pipeline_id}:summary",
            attrs={
                "pipeline_id": pipeline_id,
                "schema_version": 1,
                "status": status,
                "source_fact_ids": sorted(source_fact_ids),
                "causal_inference": False,
            },
            measures={
                "node_count": len(nodes),
                "observed_node_count": sum(value == "verified" for value in node_status.values()),
                "edge_count": len(edges),
                "verified_edge_count": verified_edges,
                "unresolved_count": unresolved_count,
            },
            facts=[node_source[node_id] for node_id in node_source],
        )
    )
    unknown = {fact.kind for fact in output} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace streaming_pipeline: {sorted(unknown)}")
    return sort_facts(output)


__all__ = ["EMITTED_KINDS", "EXTRACTOR_ID", "build_streaming_pipeline"]
