"""Composição temporal offline de progresso Structured Streaming e transporte.

O módulo só recebe :class:`Fact` já extraídos. Ele exige identidade e uma
tolerância de janela declaradas, normaliza timestamps observados sem usar o
relógio local e preserva ``unresolved`` quando uma série não pode ser pareada.
O resultado é evidência temporal; nunca é diagnóstico causal.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_temporal@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "streaming.temporal.diagnostic",
        "streaming.temporal.unresolved",
    }
)


def _subject(symbol: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": "<composition>",
        "line": 0,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _source_file(fact: Fact) -> str:
    return str((fact.subject or {}).get("file", ""))


def _provenance(facts: Sequence[Fact]) -> dict[str, Any]:
    artifacts = sorted(
        {
            str(fact.provenance.get("artifact", ""))
            for fact in facts
            if fact.provenance.get("artifact")
        }
    )
    return {
        "artifact": "<composition>",
        "artifacts": artifacts,
        "extractor": EXTRACTOR_ID,
    }


def _unresolved(
    reason: str, facts: Sequence[Fact], **attrs: Any
) -> Fact:
    return Fact(
        kind="streaming.temporal.unresolved",
        subject=_subject("temporal"),
        attrs={"reason": reason, **attrs},
        provenance=_provenance(facts),
    )


def _timestamp(fact: Fact) -> float | None:
    attrs = fact.attrs or {}
    measures = fact.measures or {}
    raw = attrs.get("observed_at", attrs.get("observedAt", attrs.get("timestamp")))
    if raw is None:
        raw = measures.get("timestamp")
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        unit = str(attrs.get("timestamp_unit", "seconds")).lower()
        if unit in {"ms", "millisecond", "milliseconds"}:
            raw = raw / 1000
        elif unit not in {"s", "sec", "second", "seconds"}:
            return None
        return float(raw) if math.isfinite(float(raw)) else None
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            value = float(raw.strip())
        except ValueError:
            return None
        return value if math.isfinite(value) else None
    if parsed.tzinfo is None:
        return None
    value = parsed.timestamp()
    return value if math.isfinite(value) else None


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


def _metric_values(fact: Fact) -> tuple[str, list[float]]:
    if fact.kind == "kafka.lag":
        key = "lag"
    elif fact.kind == "kinesis.shard":
        key = "iterator_age_ms"
    else:
        return "", []
    values = [fact.measures[key]] if isinstance(fact.measures.get(key), (int, float)) else []
    return key, [float(value) for value in values]


def build_streaming_temporal_diagnostics(
    facts: Sequence[Fact],
    *,
    query_name: str,
    transport_key: str,
    max_skew_seconds: float | None,
) -> list[Fact]:
    """Pair observed progress and transport snapshots within a declared window."""
    source_facts = list({fact.id: fact for fact in facts}.values())
    derived: list[Fact] = []
    if not query_name:
        derived.append(_unresolved("missing_declared_query_name", source_facts))
        return sort_facts(derived)
    if not transport_key:
        derived.append(_unresolved("missing_declared_transport", source_facts))
        return sort_facts(derived)
    if max_skew_seconds is None:
        derived.append(
            _unresolved(
                "missing_declared_max_skew",
                source_facts,
                max_skew_seconds_required=True,
            )
        )
        return sort_facts(derived)
    try:
        tolerance = float(max_skew_seconds)
    except (TypeError, ValueError):
        tolerance = -1
    if not math.isfinite(tolerance) or tolerance < 0:
        derived.append(
            _unresolved(
                "invalid_declared_max_skew",
                source_facts,
                max_skew_seconds=max_skew_seconds,
            )
        )
        return sort_facts(derived)

    progress = [
        fact
        for fact in source_facts
        if fact.kind == "streaming.progress.batch"
        and str((fact.attrs or {}).get("query_name", "")) == query_name
    ]
    if not progress:
        derived.append(_unresolved("query_not_found", source_facts, query_name=query_name))
        return sort_facts(derived)
    if len(progress) < 2:
        derived.append(
            _unresolved(
                "insufficient_progress_observations",
                source_facts,
                query_name=query_name,
                observed_observations=len(progress),
                required_observations=2,
            )
        )

    transport = _transport_matches(source_facts, transport_key)
    if not transport:
        derived.append(
            _unresolved(
                "transport_measurement_not_found",
                source_facts,
                transport_key=transport_key,
            )
        )
        return sort_facts(derived)

    progress_points: list[tuple[float, Fact]] = []
    missing_progress_timestamp = 0
    for fact in progress:
        timestamp = _timestamp(fact)
        if timestamp is None:
            missing_progress_timestamp += 1
        else:
            progress_points.append((timestamp, fact))
    if missing_progress_timestamp:
        derived.append(
            _unresolved(
                "missing_progress_timestamp",
                source_facts,
                query_name=query_name,
                missing_count=missing_progress_timestamp,
                required_field="timestamp",
            )
        )

    snapshots: dict[float, dict[str, Any]] = {}
    missing_transport_timestamp = 0
    missing_transport_measurement = 0
    for fact in transport:
        timestamp = _timestamp(fact)
        metric_name, values = _metric_values(fact)
        if timestamp is None:
            missing_transport_timestamp += 1
            continue
        if not values:
            missing_transport_measurement += 1
            continue
        snapshot = snapshots.setdefault(
            timestamp,
            {"facts": [], "values": [], "metrics": set(), "kinds": set()},
        )
        snapshot["facts"].append(fact)
        snapshot["values"].extend(values)
        snapshot["metrics"].add(metric_name)
        snapshot["kinds"].add(fact.kind.split(".", 1)[0])
    if missing_transport_timestamp:
        derived.append(
            _unresolved(
                "missing_transport_timestamp",
                source_facts,
                transport_key=transport_key,
                missing_count=missing_transport_timestamp,
                required_field="timestamp_or_observed_at",
            )
        )
    if missing_transport_measurement:
        derived.append(
            _unresolved(
                "missing_transport_measurement",
                source_facts,
                transport_key=transport_key,
                missing_count=missing_transport_measurement,
                required_fields=["lag", "iterator_age_ms"],
            )
        )
    if len(snapshots) < 2:
        derived.append(
            _unresolved(
                "insufficient_transport_observations",
                source_facts,
                transport_key=transport_key,
                observed_observations=len(snapshots),
                required_observations=2,
            )
        )

    remaining = sorted(snapshots.items(), key=lambda item: item[0])
    pairs: list[tuple[float, Fact, dict[str, Any], float]] = []
    for progress_timestamp, progress_fact in sorted(progress_points, key=lambda item: item[0]):
        if not remaining:
            break
        candidate_index, (transport_timestamp, snapshot) = min(
            enumerate(remaining),
            key=lambda item: (abs(item[1][0] - progress_timestamp), item[1][0]),
        )
        skew = abs(transport_timestamp - progress_timestamp)
        if skew <= tolerance:
            pairs.append((progress_timestamp, progress_fact, snapshot, skew))
            remaining.pop(candidate_index)

    if len(pairs) < 2:
        derived.append(
            _unresolved(
                "insufficient_temporal_pairs",
                source_facts,
                query_name=query_name,
                transport_key=transport_key,
                paired_observations=len(pairs),
                required_observations=2,
                max_skew_seconds=tolerance,
            )
        )
        return sort_facts(derived)

    paired_progress = [pair[1] for pair in pairs]
    paired_snapshots = [pair[2] for pair in pairs]
    transport_values = [value for snapshot in paired_snapshots for value in snapshot["values"]]
    comparable = [
        fact
        for fact in paired_progress
        if isinstance(fact.measures.get("input_rows_per_second"), (int, float))
        and isinstance(fact.measures.get("processed_rows_per_second"), (int, float))
    ]
    below_input = [
        float(fact.measures["processed_rows_per_second"])
        < float(fact.measures["input_rows_per_second"])
        for fact in comparable
    ]
    source_ids = {
        fact.id for fact in paired_progress
    }
    source_ids.update(
        fact.id for snapshot in paired_snapshots for fact in snapshot["facts"]
    )
    metrics = sorted({metric for snapshot in paired_snapshots for metric in snapshot["metrics"]})
    kinds = sorted({kind for snapshot in paired_snapshots for kind in snapshot["kinds"]})
    complete = not derived and len(pairs) == len(progress) and not remaining
    diagnostic = Fact(
        kind="streaming.temporal.diagnostic",
        subject=_subject(f"{query_name}<->{transport_key}"),
        measures={
            "progress_observation_count": len(progress),
            "transport_observation_count": len(snapshots),
            "paired_observation_count": len(pairs),
            "progress_timestamped_count": len(progress_points),
            "transport_timestamped_count": len(snapshots),
            "max_skew_seconds": max(pair[3] for pair in pairs),
            "max_transport_value": max(transport_values),
            "min_transport_value": min(transport_values),
            "comparable_progress_count": len(comparable),
        },
        attrs={
            "query_name": query_name,
            "transport_key": transport_key,
            "transport_kinds": kinds,
            "transport_metrics": metrics,
            "processed_below_input_observed": any(below_input),
            "all_paired_processed_below_input": bool(below_input) and all(below_input),
            "transport_backlog_observed": bool(transport_values),
            "temporal_window_complete": complete,
            "max_skew_seconds_declared": tolerance,
            "link_kind": "declared_temporal_window",
            "causal_inference": False,
            "source_fact_ids": sorted(source_ids),
            "progress_window_start": (paired_progress[0].attrs or {}).get("timestamp"),
            "progress_window_end": (paired_progress[-1].attrs or {}).get("timestamp"),
        },
        provenance=_provenance([*paired_progress, *transport]),
    )
    derived.append(diagnostic)
    return sort_facts(derived)


__all__ = ["EMITTED_KINDS", "EXTRACTOR_ID", "build_streaming_temporal_diagnostics"]
