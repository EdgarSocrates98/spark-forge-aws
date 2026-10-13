from __future__ import annotations

from pathlib import Path

from sparkforge_aws.facts.iceberg_metadata import extract_iceberg_metadata_path
from sparkforge_aws.facts.streaming import extract_streaming_progress_path
from sparkforge_aws.facts.streaming_composition import build_streaming_composition
from sparkforge_aws.facts.transport import extract_transport_path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_composition"


def _facts(name: str):
    directory = FIXTURES / name / "input"
    facts = list(extract_streaming_progress_path(directory / "progress.jsonl"))
    if (directory / "iceberg.json").exists():
        facts.extend(extract_iceberg_metadata_path(directory / "iceberg.json"))
    if (directory / "kafka.json").exists():
        facts.extend(extract_transport_path(directory / "kafka.json", artifact_type="kafka"))
    if (directory / "kinesis.json").exists():
        facts.extend(extract_transport_path(directory / "kinesis.json", artifact_type="kinesis"))
    return facts


def test_iceberg_link_requires_declared_identity():
    facts = build_streaming_composition(
        _facts("iceberg_non_append"), mode="iceberg", table="db.events"
    )
    unresolved = [fact for fact in facts if fact.kind == "streaming.composition.unresolved"]
    assert unresolved[0].attrs["reason"] == "missing_declared_query_name"
    assert not [fact for fact in facts if fact.kind == "streaming.iceberg.link"]


def test_observability_link_preserves_transport_measurement():
    facts = build_streaming_composition(
        _facts("observability_lag"),
        mode="observability",
        query_name="orders-query",
        transport_key="orders-group",
    )
    link = next(fact for fact in facts if fact.kind == "streaming.observability.link")
    assert link.measures["max_lag"] == 40.0
    assert link.attrs["causal_inference"] is False
    assert len(link.attrs["source_fact_ids"]) == 4


def test_kinesis_iterator_age_is_linked_by_declared_stream():
    facts = build_streaming_composition(
        _facts("observability_kinesis"),
        mode="observability",
        query_name="clicks-query",
        transport_key="clicks-stream",
    )
    link = next(fact for fact in facts if fact.kind == "streaming.observability.link")
    assert link.measures["max_iterator_age_ms"] == 2500.0
    assert link.attrs["transport_kinds"] == ["kinesis"]


def test_iceberg_temporal_pairs_progress_and_snapshots():
    facts = build_streaming_composition(
        _facts("iceberg_non_append"),
        mode="iceberg_temporal",
        table="db.events",
        query_name="orders-query",
        max_skew_seconds=0,
    )
    diagnostic = next(fact for fact in facts if fact.kind == "streaming.iceberg.temporal")
    assert diagnostic.measures["paired_observation_count"] == 2
    assert diagnostic.attrs["non_append_observed"] is True
    assert diagnostic.attrs["causal_inference"] is False
    assert len(diagnostic.attrs["source_fact_ids"]) == 4


def test_iceberg_temporal_requires_complete_window():
    facts = build_streaming_composition(
        _facts("unresolved_link"),
        mode="iceberg_temporal",
        table="db.events",
        query_name="orders-query",
        max_skew_seconds=2,
    )
    assert not [fact for fact in facts if fact.kind == "streaming.iceberg.temporal"]
    unresolved = [fact for fact in facts if fact.kind == "streaming.composition.unresolved"]
    assert unresolved
    assert unresolved[-1].attrs["reason"] == "insufficient_snapshot_observations"
