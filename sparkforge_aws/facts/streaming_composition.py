"""Composição offline de observações de streaming, transporte e Iceberg.

Este módulo não extrai arquivos e não escolhe causa. Ele recebe Facts já
extraídos, exige identidade declarada pelo chamador e produz um Fact composto
com os ids das observações de origem. Sem identidade ou com ambiguidade, emite
``streaming.composition.unresolved``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge_aws.facts.streaming_iceberg_temporal import build_streaming_iceberg_temporal
from sparkforge_aws.facts.streaming_pipeline import build_streaming_pipeline
from sparkforge_aws.facts.streaming_slo import build_streaming_slo
from sparkforge_aws.facts.streaming_temporal import build_streaming_temporal_diagnostics
from sparkforge_aws.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_composition@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "streaming.iceberg.link",
        "streaming.observability.link",
        "streaming.composition.unresolved",
        "streaming.composition.analyzed",
        "streaming.temporal.diagnostic",
        "streaming.temporal.unresolved",
        "streaming.iceberg.temporal",
        "streaming.slo.evaluation",
        "streaming.slo.unresolved",
        "streaming.pipeline.node",
        "streaming.pipeline.link",
        "streaming.pipeline",
        "streaming.pipeline.unresolved",
    }
)

_NON_APPEND = frozenset({"delete", "overwrite", "replace", "rewrite", "truncate"})


def _subject(symbol: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": "<composition>",
        "line": 0,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(facts: Sequence[Fact]) -> dict[str, Any]:
    artifacts = sorted(
        {str(f.provenance.get("artifact", "")) for f in facts if f.provenance.get("artifact")}
    )
    return {"artifact": "<composition>", "artifacts": artifacts, "extractor": EXTRACTOR_ID}


def _unresolved(mode: str, reason: str, facts: Sequence[Fact], **attrs: Any) -> Fact:
    return Fact(
        kind="streaming.composition.unresolved",
        subject=_subject(mode),
        attrs={"mode": mode, "reason": reason, **attrs},
        provenance=_provenance(facts),
    )


def _source_file(fact: Fact) -> str:
    return str((fact.subject or {}).get("file", ""))


def _unique_by_id(facts: Sequence[Fact]) -> list[Fact]:
    return list({fact.id: fact for fact in facts}.values())


def _progress_series_for_query(
    facts: Sequence[Fact], query_name: str
) -> tuple[Fact | None, Fact | None]:
    series = [fact for fact in facts if fact.kind == "streaming.progress.series"]
    if not query_name:
        if len(series) == 1:
            return series[0], None
        return None, _unresolved(
            "iceberg", "missing_declared_query_name", facts, query_name_required=True
        )

    matched: list[Fact] = []
    for candidate in series:
        source = _source_file(candidate)
        names = {
            str((fact.attrs or {}).get("query_name"))
            for fact in facts
            if fact.kind == "streaming.progress.batch"
            and _source_file(fact) == source
            and (fact.attrs or {}).get("query_name") is not None
        }
        if query_name in names:
            matched.append(candidate)
    if len(matched) == 1:
        return matched[0], None
    if not matched:
        return None, _unresolved("iceberg", "query_not_found", facts, query_name=query_name)
    return None, _unresolved(
        "iceberg", "ambiguous_query", facts, query_name=query_name, match_count=len(matched)
    )


def _iceberg_link(facts: Sequence[Fact], *, table: str, query_name: str) -> list[Fact]:
    if not table:
        return [_unresolved("iceberg", "missing_declared_table", facts)]
    if not query_name:
        return [
            _unresolved("iceberg", "missing_declared_query_name", facts, query_name_required=True)
        ]
    series, series_error = _progress_series_for_query(facts, query_name)
    if series_error is not None:
        return [series_error]
    snapshots = [
        fact
        for fact in facts
        if fact.kind == "iceberg.snapshots_summary"
        and str((fact.subject or {}).get("symbol", "")) == table
    ]
    if not snapshots:
        return [_unresolved("iceberg", "table_not_found", facts, table=table)]
    if len(snapshots) > 1:
        return [
            _unresolved(
                "iceberg", "ambiguous_table", facts, table=table, match_count=len(snapshots)
            )
        ]
    assert series is not None
    snapshot = snapshots[0]
    file_summaries = [
        fact
        for fact in facts
        if fact.kind == "iceberg.files_summary"
        and str((fact.subject or {}).get("symbol", "")) == table
    ]
    operations = [str(value) for value in (snapshot.attrs or {}).get("operations", [])]
    attrs: dict[str, Any] = {
        "table": table,
        "query_name": query_name,
        "link_kind": "declared_input",
        "operations": sorted(set(operations)),
        "non_append_operations": sorted(set(operations) & _NON_APPEND),
        "non_append_observed": bool(set(operations) & _NON_APPEND),
        "source_fact_ids": sorted({series.id, snapshot.id}),
        "causal_inference": False,
    }
    measures: dict[str, Any] = {
        "progress_observation_count": series.measures.get("observation_count"),
        "snapshot_count": snapshot.measures.get("snapshot_count"),
    }
    for key in (
        "first_batch_id",
        "last_batch_id",
        "input_rows_per_second_first",
        "input_rows_per_second_last",
        "processed_rows_per_second_first",
        "processed_rows_per_second_last",
    ):
        if key in series.measures:
            measures[key] = series.measures[key]
    for key in ("span_hours",):
        if key in snapshot.measures:
            measures[f"snapshot_{key}"] = snapshot.measures[key]
    if len(file_summaries) == 1:
        file_summary = file_summaries[0]
        for key in ("data_file_count", "avg_file_bytes", "total_file_bytes"):
            if key in file_summary.measures:
                measures[key] = file_summary.measures[key]
        attrs["source_fact_ids"] = sorted({series.id, snapshot.id, file_summary.id})
    return [
        Fact(
            kind="streaming.iceberg.link",
            subject=_subject(f"{query_name}->{table}"),
            measures=measures,
            attrs=attrs,
            provenance=_provenance([series, snapshot, *file_summaries]),
        )
    ]


def _transport_matches(facts: Sequence[Fact], transport_key: str) -> list[Fact]:
    matches: list[Fact] = []
    kinesis_sources = {
        _source_file(fact)
        for fact in facts
        if fact.kind == "kinesis.stream"
        and transport_key == str((fact.attrs or {}).get("stream_name", ""))
    }
    for fact in facts:
        attrs = fact.attrs or {}
        if fact.kind == "kafka.lag" and transport_key in {
            str(attrs.get("group", "")),
            str(attrs.get("topic", "")),
        }:
            matches.append(fact)
        elif fact.kind == "kinesis.shard" and (
            transport_key == str(attrs.get("stream_name", ""))
            or _source_file(fact) in kinesis_sources
        ):
            matches.append(fact)
    return matches


def _observability_link(
    facts: Sequence[Fact], *, transport_key: str, query_name: str
) -> list[Fact]:
    if not transport_key:
        return [_unresolved("observability", "missing_declared_transport", facts)]
    if query_name:
        series, series_error = _progress_series_for_query(facts, query_name)
        if series_error is not None:
            return [series_error]
    else:
        series_candidates = [fact for fact in facts if fact.kind == "streaming.progress.series"]
        if len(series_candidates) != 1:
            return [
                _unresolved(
                    "observability",
                    "ambiguous_progress_series",
                    facts,
                    match_count=len(series_candidates),
                )
            ]
        series = series_candidates[0]
    assert series is not None
    identity_facts = [
        fact
        for fact in facts
        if query_name
        and fact.kind == "streaming.progress.batch"
        and _source_file(fact) == _source_file(series)
        and (fact.attrs or {}).get("query_name") == query_name
    ]
    transport = _transport_matches(facts, transport_key)
    if not transport:
        return [
            _unresolved(
                "observability",
                "transport_measurement_not_found",
                facts,
                transport_key=transport_key,
            )
        ]
    kinds = sorted({fact.kind.split(".", 1)[0] for fact in transport})
    measures: dict[str, Any] = {
        "progress_observation_count": series.measures.get("observation_count"),
        "transport_measurement_count": len(transport),
    }
    lag_values = [
        float(fact.measures["lag"])
        for fact in transport
        if fact.kind == "kafka.lag" and isinstance(fact.measures.get("lag"), (int, float))
    ]
    age_values = [
        float(fact.measures["iterator_age_ms"])
        for fact in transport
        if fact.kind == "kinesis.shard"
        and isinstance(fact.measures.get("iterator_age_ms"), (int, float))
    ]
    if lag_values:
        measures["max_lag"] = max(lag_values)
        measures["lag_sum"] = sum(lag_values)
    if age_values:
        measures["max_iterator_age_ms"] = max(age_values)
    attrs = {
        "query_name": query_name or None,
        "transport_key": transport_key,
        "transport_kinds": kinds,
        "processed_below_input": bool((series.attrs or {}).get("all_processed_below_input")),
        "transport_measurement_observed": True,
        "link_kind": "declared_input",
        "causal_inference": False,
        "source_fact_ids": sorted(
            {series.id, *[fact.id for fact in identity_facts], *(fact.id for fact in transport)}
        ),
    }
    return [
        Fact(
            kind="streaming.observability.link",
            subject=_subject(f"{query_name or '<single-query>'}<->{transport_key}"),
            measures=measures,
            attrs=attrs,
            provenance=_provenance([series, *identity_facts, *transport]),
        )
    ]


def build_streaming_composition(
    facts: Sequence[Fact],
    *,
    mode: str,
    table: str = "",
    query_name: str = "",
    slo_name: str = "",
    transport_key: str = "",
    max_skew_seconds: float | None = None,
    pipeline: Mapping[str, Any] | None = None,
) -> list[Fact]:
    """Build a deterministic composition over previously extracted facts."""
    source_facts = _unique_by_id(facts)
    if mode == "iceberg":
        derived = _iceberg_link(source_facts, table=table, query_name=query_name)
    elif mode == "iceberg_temporal":
        derived = build_streaming_iceberg_temporal(
            source_facts,
            table=table,
            query_name=query_name,
            max_skew_seconds=max_skew_seconds,
        )
    elif mode == "observability":
        derived = _observability_link(
            source_facts, transport_key=transport_key, query_name=query_name
        )
    elif mode == "slo":
        derived = build_streaming_slo(
            source_facts,
            slo_name=slo_name,
            query_name=query_name,
            transport_key=transport_key,
        )
    elif mode == "temporal":
        derived = build_streaming_temporal_diagnostics(
            source_facts,
            query_name=query_name,
            transport_key=transport_key,
            max_skew_seconds=max_skew_seconds,
        )
    elif mode == "pipeline":
        derived = build_streaming_pipeline(source_facts, pipeline)
    else:
        derived = [_unresolved(mode, "unknown_mode", source_facts)]
    analyzed_attrs = {
        "mode": mode,
        "table": table or None,
        "query_name": query_name or None,
        "transport_key": transport_key or None,
        "max_skew_seconds": max_skew_seconds,
    }
    if mode == "slo" or slo_name:
        analyzed_attrs["slo_name"] = slo_name or None
    derived.append(
        Fact(
            kind="streaming.composition.analyzed",
            subject=_subject(mode),
            measures={
                "input_fact_count": len(source_facts),
                "derived_fact_count": len(derived),
                "unresolved_count": sum(f.kind.endswith(".unresolved") for f in derived),
            },
            attrs=analyzed_attrs,
            provenance=_provenance(source_facts),
        )
    )
    unknown = {fact.kind for fact in derived} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace streaming_composition: {sorted(unknown)}")
    return sort_facts([*source_facts, *derived])


__all__ = ["EMITTED_KINDS", "EXTRACTOR_ID", "build_streaming_composition"]
