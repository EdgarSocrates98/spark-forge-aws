from __future__ import annotations

import json

from sparkforge.facts.transport import extract_transport_text


def _kinds(facts):
    return {fact.kind for fact in facts}


def test_kafka_dump_emits_topic_partition_group_and_lag_facts():
    payload = {
        "cluster": {
            "cluster_id": "cluster-1",
            "version": "4.0.0",
            "security_protocol": "SASL_SSL",
        },
        "topics": [
            {
                "name": "events",
                "config": {"cleanup.policy": "compact", "retention.ms": "86400000"},
                "partitions": [
                    {"partition": 0, "leader": 1, "replicas": [1, 2], "isr": [1, 2]},
                    {"partition": 1, "leader": 2, "replicas": [1, 2], "isr": [2]},
                ],
            }
        ],
        "consumer_groups": [
            {
                "group": "orders",
                "state": "STABLE",
                "members": 2,
                "offsets": [
                    {
                        "topic": "events",
                        "partition": 0,
                        "current_offset": 10,
                        "log_end_offset": 14,
                        "lag": 4,
                    }
                ],
            }
        ],
    }
    facts = extract_transport_text(json.dumps(payload), "kafka.json", artifact="kafka")
    assert {"kafka.cluster", "kafka.topic", "kafka.partition", "kafka.consumer_group", "kafka.lag", "kafka.config", "kafka.analyzed"} <= _kinds(facts)
    partition = next(f for f in facts if f.kind == "kafka.partition" and f.measures["isr_count"] == 1)
    assert partition.measures["replication_factor"] == 2
    assert partition.measures["isr_count"] == 1
    lag = next(f for f in facts if f.kind == "kafka.lag")
    assert lag.measures["lag"] == 4
    assert lag.attrs["group"] == "orders"
    assert all(f.subject["line"] == 1 for f in facts)


def test_msk_and_kinesis_dump_emit_observed_facts():
    msk = {
        "cluster": {
            "clusterArn": "arn:aws:kafka:us-east-1:1:cluster/x",
            "currentVersion": "K3AEGXETSR30VB",
            "kafkaVersion": "3.6.0",
            "brokerType": "express",
            "encryptionInfo": {"encryptionAtRest": {"dataVolumeKMSKeyId": "key"}},
            "clientAuthentication": {"sasl": {"iam": {"enabled": True}}},
        }
    }
    kinesis = {
        "stream_name": "events",
        "stream_mode": "ON_DEMAND",
        "status": "ACTIVE",
        "shards": [
            {
                "shard_id": "shardId-000",
                "iterator_age_ms": 1200,
                "incoming_bytes": 100,
                "record_count": 3,
            }
        ],
        "metrics": [{"name": "GetRecords.IteratorAgeMilliseconds", "value": 1200, "unit": "Milliseconds"}],
    }
    msk_facts = extract_transport_text(json.dumps(msk), "msk.json", artifact="msk")
    kinesis_facts = extract_transport_text(json.dumps(kinesis), "kinesis.json", artifact="kinesis")
    assert {"msk.cluster", "msk.analyzed"} <= _kinds(msk_facts)
    assert next(f for f in msk_facts if f.kind == "msk.cluster").attrs["kafka_version"] == "3.6.0"
    assert {"kinesis.stream", "kinesis.shard", "kinesis.metric", "kinesis.analyzed"} <= _kinds(kinesis_facts)
    assert next(f for f in kinesis_facts if f.kind == "kinesis.shard").measures["iterator_age_ms"] == 1200


def test_transport_blind_spots_are_unresolved():
    bad = extract_transport_text("{not-json", "bad.json", artifact="kafka")
    unknown = extract_transport_text(json.dumps({"something": True}), "unknown.json", artifact="kinesis")
    assert any(f.kind == "kafka.unresolved" and f.attrs["reason"] == "invalid_json" for f in bad)
    assert any(f.kind == "kinesis.unresolved" and f.attrs["reason"] == "missing_shape" for f in unknown)
    assert any(f.kind == "kinesis.analyzed" for f in unknown)


def test_kinesis_api_aliases_are_normalized_without_inventing_values():
    payload = {
        "streamDescription": {
            "StreamName": "events",
            "StreamModeDetails": {"StreamMode": "PROVISIONED"},
            "Shards": [{"ShardId": "shardId-000", "IteratorAgeMilliseconds": 1200}],
        }
    }
    facts = extract_transport_text(json.dumps(payload), "kinesis-api.json", artifact="kinesis")
    stream = next(f for f in facts if f.kind == "kinesis.stream")
    shard = next(f for f in facts if f.kind == "kinesis.shard")
    assert stream.attrs["stream_name"] == "events"
    assert shard.attrs["shard_id"] == "shardId-000"
    assert shard.measures["iterator_age_ms"] == 1200
