from __future__ import annotations

import pytest

from sparkforge.facts.streaming_slo import build_streaming_slo
from sparkforge.findings.models import Fact


def _fact(kind: str, *, file: str, symbol: str = "", attrs=None, measures=None) -> Fact:
    return Fact(
        kind=kind,
        subject={"type": "source_location", "file": file, "line": 1, "col": 0, "symbol": symbol},
        attrs=attrs or {},
        measures=measures or {},
        provenance={"artifact": file, "artifact_sha256": "a" * 64, "extractor": "test@0.1.0"},
    )


def _facts(
    *, target: float = 90, metric: str = "processed_rows_per_second", window: str = "5m"
) -> list[Fact]:
    facts = [
        _fact(
            "streaming.slo",
            file="contract.json",
            symbol="throughput",
            attrs={
                "name": "throughput",
                "metric": metric,
                "operator": "gte",
                "unit": "rows_per_second",
                "window": window,
                "source": "spark_progress",
            },
            measures={"target": target},
        )
    ]
    for index, value, timestamp in (
        (1, 100, "2026-10-01T00:00:00Z"),
        (2, 90, "2026-10-01T00:05:00Z"),
        (3, 110, "2026-10-01T00:10:00Z"),
    ):
        facts.append(
            _fact(
                "streaming.progress.batch",
                file="progress.jsonl",
                attrs={"query_name": "orders-query", "timestamp": timestamp},
                measures={"batch_id": index, metric: value},
            )
        )
    return facts


def test_evaluates_direct_progress_metric():
    facts = build_streaming_slo(_facts(), slo_name="throughput", query_name="orders-query")
    evaluation = next(fact for fact in facts if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["status"] == "met"
    assert evaluation.attrs["causal_inference"] is False
    assert evaluation.measures == {
        "target": 90,
        "observed_min": 90.0,
        "observed_max": 110.0,
        "observation_count": 3,
        "observed_span_seconds": 600.0,
        "window_seconds": 300.0,
        "violated_count": 0,
    }
    assert len(evaluation.attrs["source_fact_ids"]) == 4


def test_slo_status_and_window_coverage():
    facts = build_streaming_slo(_facts(target=95), slo_name="throughput", query_name="orders-query")
    evaluation = next(fact for fact in facts if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["status"] == "violated"
    assert evaluation.measures["violated_count"] == 1
    assert evaluation.attrs["window_covered"] is True


@pytest.mark.parametrize(
    ("operator", "target", "expected"),
    [
        ("lt", 111, "met"),
        ("lte", 110, "met"),
        ("gt", 89, "met"),
        ("gte", 90, "met"),
        ("eq", 90, "violated"),
    ],
)
def test_slo_comparators(operator: str, target: float, expected: str):
    facts = _facts(target=target)
    facts[0] = Fact(
        kind=facts[0].kind,
        subject=facts[0].subject,
        attrs={**facts[0].attrs, "operator": operator},
        measures=facts[0].measures,
        provenance=facts[0].provenance,
    )
    result = build_streaming_slo(facts, slo_name="throughput", query_name="orders-query")
    evaluation = next(fact for fact in result if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["status"] == expected


@pytest.mark.parametrize(
    ("facts", "slo_name", "query_name", "reason"),
    [
        (_facts(), "throughput", "", "missing_declared_query_name"),
        (
            _facts(metric="p95_end_to_end_latency"),
            "throughput",
            "orders-query",
            "metric_not_observed",
        ),
        (_facts(window="15m"), "throughput", "orders-query", "window_not_covered"),
    ],
)
def test_slo_unresolved_reasons(facts, slo_name: str, query_name: str, reason: str):
    result = build_streaming_slo(facts, slo_name=slo_name, query_name=query_name)
    assert not [fact for fact in result if fact.kind == "streaming.slo.evaluation"]
    unresolved = [fact for fact in result if fact.kind == "streaming.slo.unresolved"]
    assert unresolved and unresolved[0].attrs["reason"] == reason


def _sink_facts(
    *,
    target: float = 90,
    metric: str = "num_output_rows",
    unit: str = "rows",
    source: str = "streaming_sink",
    sink_name: str | None = "iceberg-orders",
    descriptions: tuple[str | None, ...] = ("iceberg-orders", "iceberg-orders", "iceberg-orders"),
    values: tuple[int, ...] = (100, 90, 110),
    include_batches: bool = True,
) -> list[Fact]:
    slo_attrs = {
        "name": "sink-output",
        "metric": metric,
        "operator": "gte",
        "unit": unit,
        "window": "5m",
        "source": source,
    }
    if sink_name is not None:
        slo_attrs["sink_name"] = sink_name
    facts = [
        _fact(
            "streaming.slo",
            file="contract.json",
            symbol="sink-output",
            attrs=slo_attrs,
            measures={"target": target},
        )
    ]
    timestamps = ("2026-10-01T00:00:00Z", "2026-10-01T00:05:00Z", "2026-10-01T00:10:00Z")
    for index, (value, description) in enumerate(zip(values, descriptions, strict=True), start=1):
        facts.append(
            _fact(
                "streaming.progress.sink",
                file="progress.jsonl",
                attrs={"description": description},
                measures={"batch_id": index, "num_output_rows": value},
            )
        )
        if include_batches:
            facts.append(
                _fact(
                    "streaming.progress.batch",
                    file="progress.jsonl",
                    attrs={"query_name": "orders-query", "timestamp": timestamps[index - 1]},
                    measures={"batch_id": index},
                )
            )
    return facts


def test_evaluates_sink_output_slo():
    result = build_streaming_slo(_sink_facts(), slo_name="sink-output", query_name="orders-query")
    evaluation = next(fact for fact in result if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["status"] == "met"
    assert evaluation.attrs["observation_source"] == "streaming.progress.sink"
    assert evaluation.attrs["sink_name"] == "iceberg-orders"
    assert evaluation.measures["observed_span_seconds"] == 600.0
    assert evaluation.measures["violated_count"] == 0


def test_sink_slo_uses_batch_timestamp_and_provenance():
    result = build_streaming_slo(
        _sink_facts(target=95), slo_name="sink-output", query_name="orders-query"
    )
    evaluation = next(fact for fact in result if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["status"] == "violated"
    assert evaluation.measures["violated_count"] == 1
    assert len(evaluation.attrs["source_fact_ids"]) == 7
    assert evaluation.provenance["artifacts"] == ["contract.json", "progress.jsonl"]


@pytest.mark.parametrize(
    ("kwargs", "query_name", "reason"),
    [
        ({"include_batches": False}, "orders-query", "sink_batch_not_found"),
        ({"unit": "ms"}, "orders-query", "unit_mismatch"),
        (
            {
                "descriptions": ("iceberg-orders", "dead-letter", "iceberg-orders"),
                "sink_name": None,
            },
            "orders-query",
            "ambiguous_sink",
        ),
        ({"sink_name": "missing-sink"}, "orders-query", "sink_not_found"),
    ],
)
def test_sink_slo_unresolved_reasons(kwargs, query_name: str, reason: str):
    result = build_streaming_slo(
        _sink_facts(**kwargs), slo_name="sink-output", query_name=query_name
    )
    assert not [fact for fact in result if fact.kind == "streaming.slo.evaluation"]
    unresolved = [fact for fact in result if fact.kind == "streaming.slo.unresolved"]
    assert unresolved and unresolved[0].attrs["reason"] == reason


def _transport_facts(
    *,
    source: str = "kafka",
    metric: str = "lag",
    unit: str = "records",
    values=(40, 50, 60),
    window: str = "5m",
    target: float = 50,
    operator: str = "lte",
    transport_key: str = "orders-group",
    declared_transport_key: str | None = "orders-group",
    timestamps=("2026-10-01T00:00:00Z", "2026-10-01T00:05:00Z", "2026-10-01T00:10:00Z"),
) -> list[Fact]:
    slo_attrs = {
        "name": "transport-slo",
        "metric": metric,
        "operator": operator,
        "unit": unit,
        "window": window,
        "source": source,
    }
    if declared_transport_key is not None:
        slo_attrs["transport_key"] = declared_transport_key
    facts = [
        _fact(
            "streaming.slo",
            file="contract.json",
            symbol="transport-slo",
            attrs=slo_attrs,
            measures={"target": target},
        )
    ]
    kind = "kafka.lag" if source == "kafka" else "kinesis.shard"
    identity = (
        {"group": transport_key}
        if source == "kafka"
        else {"stream_name": transport_key, "shard_id": "shard-000"}
    )
    for value, timestamp in zip(values, timestamps, strict=True):
        facts.append(
            _fact(
                kind,
                file=f"{source}.jsonl",
                attrs={**identity, "observed_at": timestamp},
                measures={"partition": 0, metric: value}
                if source == "kafka"
                else {"iterator_age_ms": value},
            )
        )
    return facts


def test_evaluates_transport_slo_by_declared_identity():
    result = build_streaming_slo(
        _transport_facts(), slo_name="transport-slo", transport_key="orders-group"
    )
    evaluation = next(fact for fact in result if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["status"] == "violated"
    assert evaluation.attrs["transport_key"] == "orders-group"
    assert evaluation.attrs["observation_source"] == "kafka.lag"
    assert evaluation.measures["observed_span_seconds"] == 600.0
    assert evaluation.measures["violated_count"] == 1
    assert len(evaluation.attrs["source_fact_ids"]) == 4


def test_evaluates_kinesis_iterator_age_and_kafka_lag():
    result = build_streaming_slo(
        _transport_facts(
            source="kinesis",
            metric="iterator_age_ms",
            unit="ms",
            values=(1000, 1500, 2000),
            target=2000,
            operator="lte",
            transport_key="clicks-stream",
        ),
        slo_name="transport-slo",
        transport_key="clicks-stream",
    )
    evaluation = next(fact for fact in result if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["status"] == "met"
    assert evaluation.attrs["observation_source"] == "kinesis.shard"
    assert evaluation.attrs["unit"] == "ms"


def test_transport_slo_refuses_mixed_transport_series():
    facts = _transport_facts()
    facts.append(
        _fact(
            "kafka.lag",
            file="other-kafka.jsonl",
            attrs={
                "group": "orders-group",
                "topic": "returns",
                "observed_at": "2026-10-01T00:00:00Z",
            },
            measures={"partition": 0, "lag": 10},
        )
    )
    result = build_streaming_slo(facts, slo_name="transport-slo", transport_key="orders-group")
    assert not [fact for fact in result if fact.kind == "streaming.slo.evaluation"]
    unresolved = [fact for fact in result if fact.kind == "streaming.slo.unresolved"]
    assert unresolved and unresolved[0].attrs["reason"] == "ambiguous_transport"


@pytest.mark.parametrize(
    ("kwargs", "transport_key", "reason"),
    [
        ({"declared_transport_key": ""}, "", "missing_declared_transport_key"),
        (
            {"timestamps": ("not-a-timestamp", "2026-10-01T00:05:00Z", "2026-10-01T00:10:00Z")},
            "orders-group",
            "observation_timestamp_missing",
        ),
        ({"window": "15m"}, "orders-group", "window_not_covered"),
    ],
)
def test_transport_slo_unresolved_reasons(kwargs, transport_key: str, reason: str):
    result = build_streaming_slo(
        _transport_facts(**kwargs), slo_name="transport-slo", transport_key=transport_key
    )
    assert not [fact for fact in result if fact.kind == "streaming.slo.evaluation"]
    unresolved = [fact for fact in result if fact.kind == "streaming.slo.unresolved"]
    assert unresolved and unresolved[0].attrs["reason"] == reason


def test_evaluates_p95_freshness_slo():
    facts = _facts(metric="freshness_ms")
    facts[0] = Fact(
        kind=facts[0].kind,
        subject=facts[0].subject,
        attrs={
            **facts[0].attrs,
            "metric": "freshness_ms",
            "statistic": "p95",
            "unit": "ms",
            "operator": "lte",
        },
        measures={"target": 110.0},
        provenance=facts[0].provenance,
    )
    for fact, value in zip(
        [item for item in facts if item.kind == "streaming.progress.batch"],
        (100.0, 200.0, 1000.0),
        strict=True,
    ):
        fact.measures["freshness_ms"] = value

    result = build_streaming_slo(facts, slo_name="throughput", query_name="orders-query")
    evaluation = next(fact for fact in result if fact.kind == "streaming.slo.evaluation")
    assert evaluation.attrs["statistic"] == "p95"
    assert evaluation.attrs["status"] == "violated"
    assert evaluation.measures["observed_p95"] == 1000.0
    assert evaluation.measures["violated_count"] == 1
    assert len(evaluation.attrs["source_fact_ids"]) == 4


def test_end_to_end_latency_requires_explicit_measurement():
    facts = _facts(metric="batch_duration_ms")
    facts[0] = Fact(
        kind=facts[0].kind,
        subject=facts[0].subject,
        attrs={
            **facts[0].attrs,
            "metric": "end_to_end_latency_ms",
            "statistic": "p95",
            "unit": "ms",
            "operator": "lte",
        },
        measures={"target": 1000.0},
        provenance=facts[0].provenance,
    )
    for fact in [item for item in facts if item.kind == "streaming.progress.batch"]:
        fact.measures["batch_duration_ms"] = 500.0

    result = build_streaming_slo(facts, slo_name="throughput", query_name="orders-query")
    assert not [fact for fact in result if fact.kind == "streaming.slo.evaluation"]
    unresolved = [fact for fact in result if fact.kind == "streaming.slo.unresolved"]
    assert unresolved and unresolved[0].attrs["reason"] == "observation_metric_missing"
