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


def _facts(*, target: float = 90, metric: str = "processed_rows_per_second", window: str = "5m") -> list[Fact]:
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
    [("lt", 111, "met"), ("lte", 110, "met"), ("gt", 89, "met"), ("gte", 90, "met"), ("eq", 90, "violated")],
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
        (_facts(metric="p95_end_to_end_latency"), "throughput", "orders-query", "metric_not_observed"),
        (_facts(window="15m"), "throughput", "orders-query", "window_not_covered"),
    ],
)
def test_slo_unresolved_reasons(facts, slo_name: str, query_name: str, reason: str):
    result = build_streaming_slo(facts, slo_name=slo_name, query_name=query_name)
    assert not [fact for fact in result if fact.kind == "streaming.slo.evaluation"]
    unresolved = [fact for fact in result if fact.kind == "streaming.slo.unresolved"]
    assert unresolved and unresolved[0].attrs["reason"] == reason
