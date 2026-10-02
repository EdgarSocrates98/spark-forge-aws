"""Extrator offline de artefatos de transporte de streaming.

Aceita dumps JSON/JSONL já salvos de Kafka, MSK e Kinesis. Não chama brokers,
AWS ou CloudWatch. Ausência de campo é preservada como ``unresolved``; zeros
só aparecem quando o dump trouxe zero explicitamente.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_transport@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "kafka.cluster",
        "kafka.topic",
        "kafka.partition",
        "kafka.consumer_group",
        "kafka.lag",
        "kafka.config",
        "kafka.unresolved",
        "kafka.analyzed",
        "msk.cluster",
        "msk.unresolved",
        "msk.analyzed",
        "kinesis.stream",
        "kinesis.shard",
        "kinesis.metric",
        "kinesis.unresolved",
        "kinesis.analyzed",
    }
)

_ARTIFACTS = frozenset({"kafka", "msk", "kinesis"})


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _subject(artifact: str, line: int, symbol: str = "") -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": artifact,
        "line": line,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _fact(
    kind: str,
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    *,
    measures: dict[str, Any] | None = None,
    attrs: dict[str, Any] | None = None,
    symbol: str = "",
) -> Fact:
    return Fact(
        kind=kind,
        subject=_subject(artifact, line, symbol),
        measures=measures or {},
        attrs=attrs or {},
        provenance=provenance,
    )


def _unresolved(
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    domain: str,
    reason: str,
    **attrs: Any,
) -> Fact:
    return _fact(
        f"{domain}.unresolved",
        artifact,
        line,
        provenance,
        attrs={"reason": reason, **attrs},
    )


def _provenance(text: str, artifact: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }


def _as_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _records(text: str, artifact: str) -> tuple[list[tuple[int, Any]], list[tuple[int, str]]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as whole_exc:
        if not artifact.lower().endswith("jsonl"):
            return [], [(1, whole_exc.msg)]
        records: list[tuple[int, Any]] = []
        invalid: list[tuple[int, str]] = []
        for line, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                records.append((line, json.loads(raw)))
            except json.JSONDecodeError as exc:
                invalid.append((line, exc.msg))
        return records, invalid
    if isinstance(value, list):
        return [(index + 1, item) for index, item in enumerate(value)], []
    return [(1, value)], []


def _numeric_fields(record: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: number for key in keys if (number := _number(record.get(key))) is not None}


def _kafka_record(data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    facts: list[Fact] = []
    cluster = _as_dict(data.get("cluster"))
    if cluster is not None:
        attrs = {
            "cluster_id": cluster.get("cluster_id", cluster.get("clusterId")),
            "version": cluster.get("version", cluster.get("kafka_version", cluster.get("kafkaVersion"))),
            "security_protocol": cluster.get("security_protocol", cluster.get("securityProtocol")),
        }
        facts.append(
            _fact(
                "kafka.cluster",
                artifact,
                line,
                provenance,
                measures=_numeric_fields(cluster, ("broker_count", "controller_count")),
                attrs={key: value for key, value in attrs.items() if value is not None},
            )
        )
    topics = data.get("topics")
    if isinstance(topics, list):
        for topic in topics:
            if not isinstance(topic, dict):
                facts.append(_unresolved(artifact, line, provenance, "kafka", "invalid_topic_record"))
                continue
            name = topic.get("name", topic.get("topic"))
            partitions = topic.get("partitions")
            facts.append(
                _fact(
                    "kafka.topic",
                    artifact,
                    line,
                    provenance,
                    measures={"partition_count": len(partitions)} if isinstance(partitions, list) else {},
                    attrs={"name": name} if name is not None else {},
                )
            )
            config = topic.get("config")
            if isinstance(config, dict):
                for key, value in sorted(config.items(), key=lambda item: str(item[0])):
                    facts.append(
                        _fact(
                            "kafka.config",
                            artifact,
                            line,
                            provenance,
                            attrs={"topic": name, "key": str(key), "value": value},
                        )
                    )
            if isinstance(partitions, list):
                for partition in partitions:
                    if not isinstance(partition, dict):
                        facts.append(_unresolved(artifact, line, provenance, "kafka", "invalid_partition_record"))
                        continue
                    measures = _numeric_fields(
                        partition,
                        ("partition", "leader", "replication_factor", "isr_count", "log_end_offset"),
                    )
                    replicas = partition.get("replicas")
                    isr = partition.get("isr")
                    if isinstance(replicas, list):
                        measures["replication_factor"] = len(replicas)
                    if isinstance(isr, list):
                        measures["isr_count"] = len(isr)
                    facts.append(
                        _fact(
                            "kafka.partition",
                            artifact,
                            line,
                            provenance,
                            measures=measures,
                            attrs={"topic": name, "replicas": replicas, "isr": isr},
                        )
                    )
    groups = data.get("consumer_groups", data.get("groups"))
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                facts.append(_unresolved(artifact, line, provenance, "kafka", "invalid_consumer_group_record"))
                continue
            group_name = group.get("group", group.get("group_id", group.get("groupId")))
            members = group.get("members", group.get("member_count"))
            measures = {"member_count": members} if _number(members) is not None else {}
            facts.append(
                _fact(
                    "kafka.consumer_group",
                    artifact,
                    line,
                    provenance,
                    measures=measures,
                    attrs={"group": group_name, "state": group.get("state")},
                )
            )
            offsets = group.get("offsets")
            if isinstance(offsets, list):
                for offset in offsets:
                    if not isinstance(offset, dict):
                        facts.append(_unresolved(artifact, line, provenance, "kafka", "invalid_offset_record"))
                        continue
                    measures = _numeric_fields(
                        offset,
                        ("partition", "current_offset", "log_end_offset", "lag", "timestamp"),
                    )
                    if measures:
                        attrs = {"group": group_name, "topic": offset.get("topic")}
                        if isinstance(offset.get("timestamp"), str):
                            attrs["timestamp"] = offset["timestamp"]
                        for key in ("observed_at", "observedAt"):
                            if isinstance(offset.get(key), str):
                                attrs["observed_at"] = offset[key]
                                break
                        facts.append(
                            _fact(
                                "kafka.lag",
                                artifact,
                                line,
                                provenance,
                                measures=measures,
                                attrs=attrs,
                            )
                        )
                    else:
                        facts.append(_unresolved(artifact, line, provenance, "kafka", "lag_fields_missing", group=group_name))
    if not facts:
        facts.append(_unresolved(artifact, line, provenance, "kafka", "missing_shape"))
    return facts


def _msk_record(data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    cluster = _as_dict(data.get("cluster")) or data
    aliases = {
        "cluster_arn": ("clusterArn", "cluster_arn"),
        "cluster_name": ("clusterName", "cluster_name"),
        "cluster_id": ("clusterId", "cluster_id"),
        "current_version": ("currentVersion", "current_version"),
        "kafka_version": ("kafkaVersion", "kafka_version"),
        "broker_type": ("brokerType", "broker_type"),
    }
    observed = {
        normalized: next((cluster[key] for key in keys if key in cluster), None)
        for normalized, keys in aliases.items()
    }
    observed = {key: value for key, value in observed.items() if value is not None}
    encryption = _as_dict(cluster.get("encryptionInfo"))
    auth = _as_dict(cluster.get("clientAuthentication"))
    if encryption is not None:
        observed["encryption_observed"] = True
    if auth is not None:
        observed["client_authentication_observed"] = True
    facts: list[Fact] = []
    if observed:
        facts.append(
            _fact(
                "msk.cluster",
                artifact,
                line,
                provenance,
                measures=_numeric_fields(cluster, ("broker_count", "storage_gb")),
                attrs=observed,
            )
        )
    else:
        facts.append(_unresolved(artifact, line, provenance, "msk", "missing_shape"))
    return facts


def _kinesis_record(data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    facts: list[Fact] = []
    stream = _as_dict(data.get("stream")) or _as_dict(data.get("streamDescription")) or data
    def _alias(*keys: str) -> Any:
        return next((stream[key] for key in keys if key in stream), None)

    stream_attrs = {}
    if (value := _alias("stream_name", "streamName", "StreamName")) is not None:
        stream_attrs["stream_name"] = value
    if (value := _alias("stream_mode", "streamMode", "StreamMode")) is not None:
        stream_attrs["stream_mode"] = value
    mode_details = _as_dict(_alias("StreamModeDetails", "stream_mode_details"))
    if mode_details is not None and mode_details.get("StreamMode") is not None:
        stream_attrs["stream_mode"] = mode_details["StreamMode"]
    if (value := _alias("status", "stream_status", "StreamStatus")) is not None:
        stream_attrs["status"] = value
    shards = data.get("shards", stream.get("shards", stream.get("Shards")))
    if stream_attrs or isinstance(shards, list):
        facts.append(
            _fact(
                "kinesis.stream",
                artifact,
                line,
                provenance,
                measures=_numeric_fields(stream, ("open_shard_count", "retention_hours")),
                attrs=stream_attrs,
            )
        )
    if isinstance(shards, list):
        for shard in shards:
            if not isinstance(shard, dict):
                facts.append(_unresolved(artifact, line, provenance, "kinesis", "invalid_shard_record"))
                continue
            shard_measures = _numeric_fields(
                shard, ("incoming_bytes", "outgoing_bytes", "record_count", "timestamp")
            )
            for key in ("iterator_age_ms", "iterator_age_milliseconds", "IteratorAgeMilliseconds"):
                number = _number(shard.get(key))
                if number is not None:
                    shard_measures["iterator_age_ms"] = number
                    break
            shard_attrs = {
                "shard_id": next(
                    (shard[key] for key in ("shard_id", "ShardId") if key in shard),
                    None,
                ),
                "stream_name": stream_attrs.get("stream_name"),
                **{
                    key: shard[key]
                    for key in (
                        "parent_shard_id",
                        "ParentShardId",
                        "adjacent_parent_shard_id",
                        "AdjacentParentShardId",
                    )
                    if key in shard
                },
            }
            if isinstance(shard.get("timestamp"), str):
                shard_attrs["timestamp"] = shard["timestamp"]
            for key in ("observed_at", "observedAt"):
                if isinstance(shard.get(key), str):
                    shard_attrs["observed_at"] = shard[key]
                    break
            shard_attrs = {key: value for key, value in shard_attrs.items() if value is not None}
            facts.append(
                _fact(
                    "kinesis.shard",
                    artifact,
                    line,
                    provenance,
                    measures=shard_measures,
                    attrs=shard_attrs,
                )
            )
    metrics = data.get("metrics", stream.get("metrics"))
    if isinstance(metrics, dict):
        metrics = [{"name": name, "value": value} for name, value in metrics.items()]
    if isinstance(metrics, list):
        for metric in metrics:
            if not isinstance(metric, dict):
                facts.append(_unresolved(artifact, line, provenance, "kinesis", "invalid_metric_record"))
                continue
            measures = _numeric_fields(metric, ("value", "timestamp", "minimum", "maximum", "average", "sum"))
            facts.append(
                _fact(
                    "kinesis.metric",
                    artifact,
                    line,
                    provenance,
                    measures=measures,
                    attrs={key: metric[key] for key in ("name", "unit", "stream_name", "shard_id") if key in metric},
                )
            )
    if not facts:
        facts.append(_unresolved(artifact, line, provenance, "kinesis", "missing_shape"))
    return facts


def _record(data: Any, artifact: str, line: int, domain: str, provenance: dict[str, Any]) -> list[Fact]:
    if not isinstance(data, dict):
        return [_unresolved(artifact, line, provenance, domain, "invalid_record", value_type=type(data).__name__)]
    if domain == "kafka":
        return _kafka_record(data, artifact, line, provenance)
    if domain == "msk":
        return _msk_record(data, artifact, line, provenance)
    return _kinesis_record(data, artifact, line, provenance)


def extract_transport_text(text: str, artifact_path: str, *, artifact: str) -> list[Fact]:
    if artifact not in _ARTIFACTS:
        raise ValueError(f"artifact deve ser um de {sorted(_ARTIFACTS)}")
    provenance = _provenance(text, artifact_path)
    records, invalid = _records(text, artifact_path)
    facts: list[Fact] = [
        _unresolved(artifact_path, line, provenance, artifact, "invalid_json", detail=detail)
        for line, detail in invalid
    ]
    for line, record in records:
        facts.extend(_record(record, artifact_path, line, artifact, provenance))
    if not records and not invalid:
        facts.append(_unresolved(artifact_path, 1, provenance, artifact, "empty_artifact"))
    analyzed_kind = f"{artifact}.analyzed"
    facts.append(
        _fact(
            analyzed_kind,
            artifact_path,
            1,
            provenance,
            measures={"record_count": len(records), "unresolved_count": sum(f.kind.endswith(".unresolved") for f in facts)},
            attrs={"artifact_type": artifact},
        )
    )
    return sort_facts(facts)


def extract_transport_path(path: Path, *, artifact_type: str) -> list[Fact]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        provenance = _provenance(str(exc), str(path))
        return [
            _unresolved(str(path), 1, provenance, artifact_type, "unreadable_artifact", detail=str(exc)),
            _fact(f"{artifact_type}.analyzed", str(path), 1, provenance, attrs={"artifact_type": artifact_type}),
        ]
    return extract_transport_text(text, str(path), artifact=artifact_type)


def extract_transport_tree(path: Path, *, artifact_type: str) -> list[Fact]:
    facts: list[Fact] = []
    for pattern in ("*.json", "*.jsonl"):
        for child in iter_source_files(path, pattern):
            facts.extend(extract_transport_path(child, artifact_type=artifact_type))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_transport_path",
    "extract_transport_text",
    "extract_transport_tree",
]
