import json
from pathlib import Path

from sparkforge.facts.glue_streaming import extract_glue_streaming_path

FIXTURES = Path(__file__).parents[1] / "fixtures" / "glue_streaming"


def test_rtm_dump_emits_observed_constraints_and_capacity():
    facts = extract_glue_streaming_path(FIXTURES / "rtm_valid" / "input" / "job.json")
    job = next(f for f in facts if f.kind == "glue.streaming.job")
    assert job.attrs["mode"] == "REAL_TIME"
    assert job.attrs["language"] == "SCALA"
    assert job.attrs["source_type"] == "KAFKA"
    assert job.measures["partition_count"] == 4
    assert job.measures["task_slots"] == 4
    assert not any(f.kind == "glue.streaming.unresolved" for f in facts)


def test_rtm_missing_capacity_is_unresolved_not_zero():
    facts = extract_glue_streaming_path(FIXTURES / "rtm_missing_capacity" / "input" / "job.json")
    unresolved = [f for f in facts if f.kind == "glue.streaming.unresolved"]
    assert any(f.attrs["reason"] == "partition_capacity" for f in unresolved)
    job = next(f for f in facts if f.kind == "glue.streaming.job")
    assert "partition_count" not in job.measures
    assert "task_slots" not in job.measures


def test_stream_endpoints_emit_explicit_facts(tmp_path):
    path = tmp_path / "job.json"
    path.write_text(
        json.dumps(
            {
                "job": {
                    "name": "endpoint-contract",
                    "stream": {
                        "sources": [
                            {
                                "source_id": "orders-source",
                                "connector": "kafka",
                                "topic": "orders",
                                "partition_count": 12,
                                "lag_records": 7,
                                "nested": {"must_not": "leak"},
                            }
                        ],
                        "sink": {
                            "sink_id": "orders-sink",
                            "connector": "iceberg",
                            "table": "prod.orders",
                            "num_records_out": 98,
                            "pending_commits": 1,
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    facts = extract_glue_streaming_path(path)
    source = next(f for f in facts if f.kind == "glue.streaming.source")
    sink = next(f for f in facts if f.kind == "glue.streaming.sink")

    assert source.attrs["source_id"] == "orders-source"
    assert source.attrs["connector"] == "kafka"
    assert source.measures == {"lag_records": 7, "partition_count": 12}
    assert sink.attrs["sink_id"] == "orders-sink"
    assert sink.attrs["connector"] == "iceberg"
    assert sink.measures == {"num_records_out": 98, "pending_commits": 1}
    assert "nested" not in source.attrs
    assert not any(f.kind == "glue.streaming.unresolved" for f in facts)


def test_stream_endpoints_preserve_observed_fields_only(tmp_path):
    path = tmp_path / "job.json"
    path.write_text(
        json.dumps(
            {
                "job": {
                    "stream": {
                        "source": {
                            "sourceId": "kinesis-source",
                            "sourceType": "KINESIS",
                            "deliverySemantics": "at_least_once",
                            "shard_count": 3,
                            "enabled": True,
                        },
                        "sinks": [
                            {
                                "id": "s3-sink",
                                "type": "S3",
                                "format": "parquet",
                                "write_failures": 0,
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    facts = extract_glue_streaming_path(path)
    source = next(f for f in facts if f.kind == "glue.streaming.source")
    sink = next(f for f in facts if f.kind == "glue.streaming.sink")

    assert source.attrs == {
        "source_id": "kinesis-source",
        "type": "KINESIS",
        "delivery_semantics": "at_least_once",
        "enabled": True,
    }
    assert source.measures == {"shard_count": 3}
    assert sink.attrs == {"sink_id": "s3-sink", "type": "S3", "format": "parquet"}
    assert sink.measures == {"write_failures": 0}


def test_stream_endpoint_absence_is_unresolved():
    facts = extract_glue_streaming_path(FIXTURES / "rtm_missing_capacity" / "input" / "job.json")
    reasons = {
        f.attrs["reason"]
        for f in facts
        if f.kind == "glue.streaming.unresolved"
    }
    assert {"source_metrics_missing", "sink_metrics_missing"} <= reasons


def test_stream_endpoint_invalid_shape_is_unresolved(tmp_path):
    path = tmp_path / "job.json"
    path.write_text(
        json.dumps({"job": {"stream": {"sources": "kafka", "sinks": [None, {}]}}}),
        encoding="utf-8",
    )

    facts = extract_glue_streaming_path(path)
    reasons = [
        f.attrs["reason"]
        for f in facts
        if f.kind == "glue.streaming.unresolved"
    ]
    assert "sources_not_a_list" in reasons
    assert "invalid_sink_record" in reasons
    assert "sink_fields_missing" in reasons
