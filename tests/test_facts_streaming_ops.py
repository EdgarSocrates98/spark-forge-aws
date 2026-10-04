from __future__ import annotations

from pathlib import Path

from sparkforge.facts.streaming_ops import extract_streaming_ops_path

ROOT = Path(__file__).resolve().parents[1]


def test_streaming_ops_preserves_declared_metrics_without_secret_values():
    facts = extract_streaming_ops_path(
        ROOT / "fixtures/streaming_ops/declared_complete/input/contract.json"
    )
    assert {fact.kind for fact in facts} >= {
        "streaming.slo",
        "streaming.finops",
        "streaming.security",
        "streaming.serving",
        "streaming.lakehouse",
    }
    slo = next(fact for fact in facts if fact.kind == "streaming.slo")
    assert slo.measures["target"] == 5000
    assert slo.attrs["metric"] == "p95_end_to_end_latency"


def test_streaming_ops_redacts_secret_like_fields():
    facts = extract_streaming_ops_path(
        ROOT / "fixtures/streaming_ops/redaction/input/contract.json"
    )
    unresolved = [fact for fact in facts if fact.kind == "streaming_ops.unresolved"]
    assert any("artifact_secret_redacted" in fact.attrs["reason"] for fact in unresolved)
    serialized = str([fact.to_dict() for fact in facts])
    assert "must-not-persist" not in serialized


def test_slo_preserves_statistic_attribute(tmp_path):
    path = tmp_path / "contract.json"
    path.write_text(
        '{"slo":[{"name":"freshness","metric":"freshness_ms","target":15000,'
        '"operator":"lte","unit":"ms","window":"5m","source":"spark_progress",'
        '"statistic":"p95"}],"finops":[],"security":[],"serving":[],"lakehouse":[]}',
        encoding="utf-8",
    )

    facts = extract_streaming_ops_path(path)

    slo = next(fact for fact in facts if fact.kind == "streaming.slo")
    assert slo.attrs["statistic"] == "p95"

    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        '{"slo":[{"name":"freshness","metric":"freshness_ms","target":15000,'
        '"operator":"lte","unit":"ms","window":"5m","source":"spark_progress",'
        '"statistic":"p99"}],"finops":[],"security":[],"serving":[],"lakehouse":[]}',
        encoding="utf-8",
    )
    invalid_facts = extract_streaming_ops_path(invalid)
    assert not [fact for fact in invalid_facts if fact.kind == "streaming.slo"]
    assert any(
        fact.attrs["reason"] == "slo_statistic_unsupported:freshness"
        for fact in invalid_facts
        if fact.kind == "streaming_ops.unresolved"
    )
