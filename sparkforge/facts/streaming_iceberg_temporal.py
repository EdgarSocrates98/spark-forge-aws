"""Offline temporal composition between streaming progress and Iceberg snapshots.

The module receives facts already extracted from both artifacts. It pairs
observed timestamps inside a caller-declared window and emits one compact fact
with source ids. It never infers order from file position, uses local time, or
claims that a snapshot caused a streaming symptom.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import math
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_iceberg_temporal@0.1.0"
EMITTED_KINDS = frozenset({"streaming.iceberg.temporal"})
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


def _source_file(fact: Fact) -> str:
    return str((fact.subject or {}).get("file", ""))


def _provenance(facts: Sequence[Fact]) -> dict[str, Any]:
    return {
        "artifact": "<composition>",
        "artifacts": sorted(
            {
                str(fact.provenance.get("artifact", ""))
                for fact in facts
                if fact.provenance.get("artifact")
            }
        ),
        "extractor": EXTRACTOR_ID,
    }


def _unresolved(reason: str, facts: Sequence[Fact], **attrs: Any) -> Fact:
    return Fact(
        kind="streaming.composition.unresolved",
        subject=_subject("iceberg_temporal"),
        attrs={"mode": "iceberg_temporal", "reason": reason, **attrs},
        provenance=_provenance(facts),
    )


def _timestamp(raw: Any) -> float | None:
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if math.isfinite(value) else None
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    value = parsed.timestamp()
    return value if math.isfinite(value) else None


def _progress_timestamp(fact: Fact) -> float | None:
    attrs = fact.attrs or {}
    return _timestamp(attrs.get("observed_at", attrs.get("timestamp")))


def _snapshot_timestamp(fact: Fact) -> float | None:
    return _timestamp((fact.attrs or {}).get("committed_at"))


def build_streaming_iceberg_temporal(
    facts: Sequence[Fact],
    *,
    table: str,
    query_name: str,
    max_skew_seconds: float | None,
) -> list[Fact]:
    """Pair two or more observed progress batches and Iceberg snapshots."""
    source_facts = list({fact.id: fact for fact in facts}.values())
    if not table:
        return [_unresolved("missing_declared_table", source_facts)]
    if not query_name:
        return [_unresolved("missing_declared_query_name", source_facts)]
    if max_skew_seconds is None:
        return [_unresolved("missing_declared_max_skew", source_facts)]
    try:
        tolerance = float(max_skew_seconds)
    except (TypeError, ValueError):
        tolerance = -1
    if not math.isfinite(tolerance) or tolerance < 0:
        return [_unresolved("invalid_declared_max_skew", source_facts, max_skew_seconds=max_skew_seconds)]

    progress = [
        fact
        for fact in source_facts
        if fact.kind == "streaming.progress.batch"
        and str((fact.attrs or {}).get("query_name", (fact.attrs or {}).get("name", ""))) == query_name
    ]
    snapshots = [
        fact
        for fact in source_facts
        if fact.kind == "iceberg.snapshot"
        and str((fact.subject or {}).get("symbol", "")) == table
    ]
    if not progress:
        return [_unresolved("query_not_found", source_facts, query_name=query_name)]
    if not snapshots:
        return [_unresolved("table_snapshots_not_found", source_facts, table=table)]
    if len(progress) < 2:
        return [_unresolved("insufficient_progress_observations", source_facts, observed_observations=len(progress), required_observations=2)]
    if len(snapshots) < 2:
        return [_unresolved("insufficient_snapshot_observations", source_facts, observed_observations=len(snapshots), required_observations=2)]

    progress_points: list[tuple[float, Fact]] = []
    for fact in progress:
        timestamp = _progress_timestamp(fact)
        if timestamp is None:
            return [_unresolved("missing_progress_timestamp", source_facts, query_name=query_name)]
        progress_points.append((timestamp, fact))
    snapshot_points: list[tuple[float, Fact]] = []
    for fact in snapshots:
        timestamp = _snapshot_timestamp(fact)
        if timestamp is None:
            return [_unresolved("missing_snapshot_timestamp", source_facts, table=table)]
        snapshot_points.append((timestamp, fact))

    remaining = sorted(snapshot_points, key=lambda item: (item[0], item[1].id))
    pairs: list[tuple[float, Fact, Fact, float]] = []
    for progress_timestamp, progress_fact in sorted(progress_points, key=lambda item: (item[0], item[1].id)):
        if not remaining:
            break
        index, (snapshot_timestamp, snapshot_fact) = min(
            enumerate(remaining),
            key=lambda item: (abs(item[1][0] - progress_timestamp), item[1][0], item[1][1].id),
        )
        skew = abs(snapshot_timestamp - progress_timestamp)
        if skew <= tolerance:
            pairs.append((progress_timestamp, progress_fact, snapshot_fact, skew))
            remaining.pop(index)

    if len(pairs) < 2:
        return [
            _unresolved(
                "insufficient_temporal_pairs",
                source_facts,
                table=table,
                query_name=query_name,
                paired_observations=len(pairs),
                required_observations=2,
                max_skew_seconds=tolerance,
            )
        ]

    paired_snapshots = [pair[2] for pair in pairs]
    operations = sorted(
        {
            str((fact.attrs or {}).get("operation"))
            for fact in paired_snapshots
            if (fact.attrs or {}).get("operation")
        }
    )
    source_ids = sorted(
        {fact.id for _, progress_fact, snapshot_fact, _ in pairs for fact in (progress_fact, snapshot_fact)}
    )
    diagnostic = Fact(
        kind="streaming.iceberg.temporal",
        subject=_subject(f"{query_name}->{table}"),
        measures={
            "progress_observation_count": len(progress),
            "snapshot_observation_count": len(snapshots),
            "paired_observation_count": len(pairs),
            "progress_timestamped_count": len(progress_points),
            "snapshot_timestamped_count": len(snapshot_points),
            "max_skew_seconds": max(pair[3] for pair in pairs),
            "non_append_snapshot_count": sum(
                1 for fact in paired_snapshots if (fact.attrs or {}).get("operation") in _NON_APPEND
            ),
        },
        attrs={
            "table": table,
            "query_name": query_name,
            "operations": operations,
            "non_append_observed": bool(set(operations) & _NON_APPEND),
            "temporal_window_complete": len(pairs) == len(progress) == len(snapshots),
            "max_skew_seconds_declared": tolerance,
            "source_fact_ids": source_ids,
            "progress_window_start": (pairs[0][1].attrs or {}).get("timestamp"),
            "progress_window_end": (pairs[-1][1].attrs or {}).get("timestamp"),
            "snapshot_window_start": (pairs[0][2].attrs or {}).get("committed_at"),
            "snapshot_window_end": (pairs[-1][2].attrs or {}).get("committed_at"),
            "link_kind": "declared_temporal_window",
            "causal_inference": False,
        },
        provenance=_provenance([fact for _, progress_fact, snapshot_fact, _ in pairs for fact in (progress_fact, snapshot_fact)]),
    )
    return [diagnostic]


__all__ = ["EMITTED_KINDS", "EXTRACTOR_ID", "build_streaming_iceberg_temporal"]
