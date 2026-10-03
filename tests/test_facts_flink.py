from __future__ import annotations

import json

from sparkforge.facts.flink import extract_flink_text


def _kinds(facts):
    return {fact.kind for fact in facts}


def test_flink_dump_emits_job_operator_checkpoint_state():
    payload = {
        "job": {"job_id": "job-1", "name": "orders", "api": "DataStream", "version": "2.3.0", "parallelism": 4},
        "operators": [
            {"operator_id": "op-1", "name": "aggregate", "uid": "aggregate", "backpressured_ratio": 0.25, "busy_ratio": 0.7}
        ],
        "checkpoints": [
            {"id": 7, "status": "COMPLETED", "duration_ms": 1200, "alignment_ms": 180, "state_size_bytes": 4096}
        ],
        "state": [{"backend": "rocksdb", "operator_id": "op-1", "size_bytes": 4096, "num_entries": 12}],
    }
    facts = extract_flink_text(json.dumps(payload), "flink.json", artifact="flink")
    assert {"flink.job", "flink.operator", "flink.checkpoint", "flink.state", "flink.analyzed"} <= _kinds(facts)
    assert next(f for f in facts if f.kind == "flink.operator").measures["backpressured_ratio"] == 0.25
    assert next(f for f in facts if f.kind == "flink.checkpoint").measures["alignment_ms"] == 180


def test_flink_dump_emits_explicit_source_and_sink():
    payload = {
        "job": {"name": "orders", "parallelism": 4},
        "sources": [
            {
                "sourceId": "orders-source",
                "name": "Kafka orders",
                "uid": "source-orders",
                "type": "KafkaSource",
                "connector": "kafka",
                "parallelism": 4,
                "backlog_records": 12,
                "num_records_in": 1000,
            }
        ],
        "sinks": {
            "sink_id": "orders-sink",
            "name": "Iceberg orders",
            "type": "IcebergSink",
            "connector": "iceberg",
            "parallelism": 4,
            "pending_commits": 1,
            "num_records_out": 998,
        },
    }

    facts = extract_flink_text(json.dumps(payload), "flink.json", artifact="flink")
    assert {"flink.source", "flink.sink"} <= _kinds(facts)
    source = next(f for f in facts if f.kind == "flink.source")
    sink = next(f for f in facts if f.kind == "flink.sink")
    assert source.attrs["source_id"] == "orders-source"
    assert source.measures["backlog_records"] == 12
    assert sink.attrs["sink_id"] == "orders-sink"
    assert sink.measures["pending_commits"] == 1


def test_flink_source_sink_preserve_observed_fields_only():
    payload = {
        "sources": [{"id": "source-1", "connector": "kinesis", "parallelism": 2}],
        "sinks": [{"id": "sink-1", "connector": "iceberg", "commit_failures": 0}],
    }

    facts = extract_flink_text(json.dumps(payload), "flink.json", artifact="flink")
    source = next(f for f in facts if f.kind == "flink.source")
    sink = next(f for f in facts if f.kind == "flink.sink")
    assert source.attrs == {"source_id": "source-1", "connector": "kinesis"}
    assert source.measures == {"parallelism": 2}
    assert sink.attrs == {"sink_id": "sink-1", "connector": "iceberg"}
    assert sink.measures == {"commit_failures": 0}
    assert "backlog_records" not in source.measures
    assert "pending_commits" not in sink.measures


def test_flink_source_sink_absence_is_unresolved():
    facts = extract_flink_text(json.dumps({"job": {"name": "partial"}}), "partial.json", artifact="flink")
    unresolved = [fact.attrs["reason"] for fact in facts if fact.kind == "flink.unresolved"]
    assert "source_metrics_missing" in unresolved
    assert "sink_metrics_missing" in unresolved


def test_flink_source_sink_invalid_shapes_are_unresolved():
    payload = {"sources": "not-a-list", "sinks": ["not-an-object"]}
    facts = extract_flink_text(json.dumps(payload), "invalid.json", artifact="flink")
    unresolved = {fact.attrs["reason"] for fact in facts if fact.kind == "flink.unresolved"}
    assert {"sources_not_a_list", "invalid_sink_record"} <= unresolved


def test_managed_flink_dump_keeps_service_namespace():
    payload = {
        "application": {"applicationName": "orders-prod", "runtimeVersion": "1.20", "status": "RUNNING", "parallelism": 2},
        "configuration": {"checkpointing.interval": "60s", "state.backend": "rocksdb"},
        "connectors": [{"name": "kinesis", "type": "source"}],
        "metrics": [{"name": "busyTimeMsPerSecond", "value": 800}],
    }
    facts = extract_flink_text(json.dumps(payload), "managed.json", artifact="managed_flink")
    assert {"managed_flink.application", "managed_flink.config", "managed_flink.connector", "managed_flink.metric", "managed_flink.analyzed"} <= _kinds(facts)
    assert not any(f.kind.startswith("flink.") for f in facts)
    assert next(f for f in facts if f.kind == "managed_flink.application").attrs["runtime_version"] == "1.20"


def test_flink_missing_metrics_are_unresolved_not_zero():
    facts = extract_flink_text(json.dumps({"job": {"name": "partial"}}), "partial.json", artifact="flink")
    unresolved = [f for f in facts if f.kind == "flink.unresolved"]
    assert any(f.attrs["reason"] == "checkpoint_metrics_missing" for f in unresolved)
    assert all("duration_ms" not in f.measures for f in facts if f.kind == "flink.checkpoint")


def test_managed_flink_missing_metrics_are_unresolved():
    facts = extract_flink_text(json.dumps({"application": {"name": "partial"}}), "partial.json", artifact="managed_flink")
    assert any(f.kind == "managed_flink.unresolved" and f.attrs["reason"] == "metrics_missing" for f in facts)
