from __future__ import annotations

from datetime import datetime, timezone

from sparkforge.facts.streaming_temporal import build_streaming_temporal_diagnostics
from sparkforge.findings.models import Fact


def _fact(kind: str, *, attrs=None, measures=None, symbol: str = "") -> Fact:
    return Fact(
        kind=kind,
        subject={
            "type": "source_location",
            "file": "fixture.jsonl",
            "line": 1,
            "col": 0,
            "symbol": symbol,
        },
        attrs=attrs or {},
        measures=measures or {},
        provenance={
            "artifact": "fixture.jsonl",
            "artifact_sha256": "a" * 64,
            "extractor": "test@0.1.0",
        },
    )


def _epoch(value: str) -> float:
    return (
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )


def _facts(*, complete: bool = True) -> list[Fact]:
    progress = [
        _fact(
            "streaming.progress.batch",
            attrs={"query_name": "orders-query", "timestamp": "2026-10-02T12:00:00Z"},
            measures={"batch_id": 1, "input_rows_per_second": 100, "processed_rows_per_second": 80},
        ),
        _fact(
            "streaming.progress.batch",
            attrs={"query_name": "orders-query", "timestamp": "2026-10-02T12:00:10Z"},
            measures={"batch_id": 2, "input_rows_per_second": 110, "processed_rows_per_second": 90},
        ),
    ]
    transport = [
        _fact(
            "kafka.lag",
            attrs={"group": "orders-group", "topic": "orders"},
            measures={"partition": 0, "lag": 30, "timestamp": _epoch("2026-10-02T12:00:01Z")},
        ),
        _fact(
            "kafka.lag",
            attrs={"group": "orders-group", "topic": "orders"},
            measures={"partition": 0, "lag": 40, "timestamp": _epoch("2026-10-02T12:00:12Z")},
        ),
    ]
    if not complete:
        transport[1].measures.pop("timestamp")
    return [*progress, *transport]


def test_temporal_pairing_preserves_source_ids_and_skew():
    facts = build_streaming_temporal_diagnostics(
        _facts(),
        query_name="orders-query",
        transport_key="orders-group",
        max_skew_seconds=3,
    )

    diagnostic = next(fact for fact in facts if fact.kind == "streaming.temporal.diagnostic")
    assert diagnostic.measures["paired_observation_count"] == 2
    assert diagnostic.measures["max_skew_seconds"] == 2.0
    assert diagnostic.measures["max_transport_value"] == 40.0
    assert len(diagnostic.attrs["source_fact_ids"]) == 4
    assert diagnostic.attrs["causal_inference"] is False
    assert diagnostic.attrs["temporal_window_complete"] is True
    assert diagnostic.attrs["all_paired_processed_below_input"] is True


def test_temporal_requires_timestamps_and_declared_window():
    unresolved = build_streaming_temporal_diagnostics(
        _facts(complete=False),
        query_name="orders-query",
        transport_key="orders-group",
        max_skew_seconds=None,
    )
    reasons = {
        fact.attrs["reason"] for fact in unresolved if fact.kind == "streaming.temporal.unresolved"
    }
    assert "missing_declared_max_skew" in reasons
    assert not [fact for fact in unresolved if fact.kind == "streaming.temporal.diagnostic"]

    partial = build_streaming_temporal_diagnostics(
        _facts(complete=False),
        query_name="orders-query",
        transport_key="orders-group",
        max_skew_seconds=3,
    )
    assert any(
        fact.attrs["reason"] == "missing_transport_timestamp"
        for fact in partial
        if fact.kind == "streaming.temporal.unresolved"
    )
