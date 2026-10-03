"""Extrai fatos offline de CDC, Debezium/Kafka Connect e AWS DMS.

O módulo consome dumps JSON/JSONL já salvos. Não chama banco, Kafka Connect,
Debezium ou AWS DMS. Posições, chaves, transações e estados ausentes ficam
nomeados como ``unresolved``; nenhum offset, delete ou capacidade é inferido.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "cdc@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "cdc.connector",
        "cdc.snapshot",
        "cdc.event",
        "cdc.transaction",
        "cdc.duplicate",
        "cdc.unresolved",
        "cdc.analyzed",
        "debezium.connector",
        "debezium.status",
        "debezium.unresolved",
        "debezium.analyzed",
        "dms.task",
        "dms.endpoint",
        "dms.mapping",
        "dms.stats",
        "dms.unresolved",
        "dms.analyzed",
    }
)

_ARTIFACTS = frozenset({"cdc", "debezium", "dms"})


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
    domain: str,
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    reason: str,
    **attrs: Any,
) -> Fact:
    return _fact(f"{domain}.unresolved", artifact, line, provenance, attrs={"reason": reason, **attrs})


def _provenance(text: str, artifact: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return None


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _records(text: str, artifact: str) -> tuple[list[tuple[int, Any]], list[tuple[int, str]]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        if not artifact.lower().endswith("jsonl"):
            return [], [(1, exc.msg)]
        records: list[tuple[int, Any]] = []
        invalid: list[tuple[int, str]] = []
        for line, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                records.append((line, json.loads(raw)))
            except json.JSONDecodeError as line_exc:
                invalid.append((line, line_exc.msg))
        return records, invalid
    if isinstance(value, list):
        return [(index + 1, item) for index, item in enumerate(value)], []
    return [(1, value)], []


def _mapping_rules(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        nested = value.get("rules", value.get("Rules"))
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
    return []


def _extract_debezium(data: Any, artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    if not isinstance(data, dict):
        return [_unresolved("debezium", artifact, line, provenance, "invalid_connector_record")]
    config = data.get("connector", data.get("config", data))
    if not isinstance(config, dict):
        return [_unresolved("debezium", artifact, line, provenance, "missing_connector_config")]
    def value(*keys: str) -> Any:
        for key in keys:
            if key in config:
                return config[key]
        return None

    connector_class = _text(value("connector.class", "connector_class", "class"))
    database = _text(value("database", "database.hostname", "database.server.name"))
    snapshot_mode = _text(value("snapshot.mode", "snapshot_mode"))
    topic_prefix = _text(value("topic.prefix", "topic_prefix", "database.server.name"))
    heartbeat = _text(value("heartbeat.interval.ms", "heartbeat_interval_ms", "heartbeat"))
    history = _text(value("schema.history.internal", "schema_history", "database.history"))
    transforms = _text(value("transforms"))
    delete_handling = _text(value("delete.handling.mode", "delete_handling"))
    tombstones = _bool(value("tombstones.on.delete", "tombstones_on_delete"))
    transactions = _bool(value("provide.transaction.metadata", "transaction_metadata"))
    outbox = _bool(value("outbox", "outbox.enabled"))
    attrs = {
        key: item
        for key, item in {
            "name": _text(value("name", "connector.name")),
            "connector_class": connector_class,
            "database": database,
            "snapshot_mode": snapshot_mode,
            "topic_prefix": topic_prefix,
            "heartbeat": heartbeat,
            "schema_history": history,
            "transforms": transforms,
            "delete_handling": delete_handling,
            "tombstones_on_delete": tombstones,
            "transaction_metadata": transactions,
            "outbox": outbox,
            "key_converter": _text(value("key.converter", "key_converter")),
            "value_converter": _text(value("value.converter", "value_converter")),
            "error_tolerance": _text(value("errors.tolerance", "error_tolerance")),
        }.items()
        if item is not None
    }
    facts: list[Fact] = [
        _fact("debezium.connector", artifact, line, provenance, attrs=attrs, symbol=attrs.get("name", "")),
        _fact("debezium.analyzed", artifact, line, provenance, attrs={"domain": "debezium"}),
    ]
    status = data.get("status", data.get("connect_status"))
    if isinstance(status, dict):
        task_states = status.get("tasks", [])
        states = [item.get("state") for item in task_states if isinstance(item, dict) and item.get("state")]
        facts.append(
            _fact(
                "debezium.status",
                artifact,
                line,
                provenance,
                measures={"task_count": len(task_states)},
                attrs={"connector_state": status.get("connector", {}).get("state") if isinstance(status.get("connector"), dict) else status.get("state"), "task_states": states},
            )
        )
    for field, reason in ((connector_class, "connector_class"), (snapshot_mode, "snapshot_mode"), (topic_prefix, "topic_prefix")):
        if field is None:
            facts.append(_unresolved("debezium", artifact, line, provenance, f"missing_{reason}"))
    if history is None:
        facts.append(_unresolved("debezium", artifact, line, provenance, "schema_history"))
    if tombstones is None and delete_handling is not None:
        facts.append(_unresolved("debezium", artifact, line, provenance, "delete_tombstone_behavior"))
    return facts


def _extract_dms(data: Any, artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    if not isinstance(data, dict):
        return [_unresolved("dms", artifact, line, provenance, "invalid_task_record")]
    task = data.get("task", data.get("replication_task", data))
    task = task if isinstance(task, dict) else {}
    migration_type = _text(task.get("migration_type", task.get("MigrationType", data.get("migration_type"))))
    name = _text(task.get("name", task.get("ReplicationTaskIdentifier", data.get("name"))))
    settings = task.get("settings", task.get("ReplicationTaskSettings", data.get("settings", {})))
    settings = settings if isinstance(settings, dict) else {}
    validation = _bool(task.get("validation_enabled", settings.get("ValidationSettings", {}).get("EnableValidation") if isinstance(settings.get("ValidationSettings"), dict) else None))
    attrs = {
        key: item
        for key, item in {
            "name": name,
            "migration_type": migration_type.upper() if migration_type else None,
            "status": _text(task.get("status", task.get("Status"))),
            "source_engine": _text(task.get("source_engine", task.get("SourceEndpointEngine"))),
            "target_engine": _text(task.get("target_engine", task.get("TargetEndpointEngine"))),
            "validation_enabled": validation,
            "recovery_table": _bool(task.get("recovery_table", settings.get("ControlTablesSettings", {}).get("ControlSchema") if isinstance(settings.get("ControlTablesSettings"), dict) else None)),
            "cdc_start_position": _text(task.get("cdc_start_position", task.get("CdcStartPosition"))),
        }.items()
        if item is not None
    }
    facts: list[Fact] = [
        _fact("dms.task", artifact, line, provenance, attrs=attrs, symbol=name or ""),
        _fact("dms.analyzed", artifact, line, provenance, attrs={"domain": "dms"}),
    ]
    for endpoint_key, endpoint_type in (("source_endpoint", "SOURCE"), ("target_endpoint", "TARGET")):
        endpoint = data.get(endpoint_key, data.get(endpoint_key.replace("_", "")))
        if isinstance(endpoint, dict):
            endpoint_attrs = {
                key: item
                for key, item in {
                    "endpoint_type": endpoint_type,
                    "engine": _text(endpoint.get("engine", endpoint.get("EngineName"))),
                    "server": _text(endpoint.get("server", endpoint.get("ServerName"))),
                    "port": _number(endpoint.get("port", endpoint.get("Port"))),
                    "status": _text(endpoint.get("status", endpoint.get("Status"))),
                }.items()
                if item is not None
            }
            measures = {"port": endpoint_attrs.pop("port")} if "port" in endpoint_attrs else {}
            facts.append(_fact("dms.endpoint", artifact, line, provenance, measures=measures, attrs=endpoint_attrs))
        else:
            facts.append(_unresolved("dms", artifact, line, provenance, f"missing_{endpoint_type.lower()}_endpoint"))
    mapping_rules = _mapping_rules(data.get("table_mappings", data.get("TableMappings")))
    for mapping in mapping_rules:
        locator = mapping.get("object_locator", mapping.get("objectLocator", {}))
        locator = locator if isinstance(locator, dict) else {}
        facts.append(
            _fact(
                "dms.mapping",
                artifact,
                line,
                provenance,
                attrs={
                    "rule_type": _text(mapping.get("rule_type", mapping.get("ruleType"))),
                    "rule_action": _text(mapping.get("rule_action", mapping.get("ruleAction"))),
                    "schema": _text(locator.get("schema_name", locator.get("schemaName"))),
                    "table": _text(locator.get("table_name", locator.get("tableName"))),
                    "target_schema": _text(mapping.get("target_schema", mapping.get("targetSchema"))),
                    "target_table": _text(mapping.get("target_table", mapping.get("targetTable"))),
                    "key_columns_declared": mapping.get("key_columns", mapping.get("keyColumns")),
                },
            )
        )
    if not mapping_rules:
        facts.append(_unresolved("dms", artifact, line, provenance, "missing_table_mappings"))
    if migration_type and migration_type.upper() in {"FULL-LOAD-AND-CDC", "FULL_LOAD_AND_CDC", "FULL LOAD AND CDC"} and not attrs.get("cdc_start_position"):
        facts.append(_unresolved("dms", artifact, line, provenance, "snapshot_cdc_seam"))
    stats = data.get("stats", data.get("table_statistics", []))
    if isinstance(stats, list):
        for stat in stats:
            if not isinstance(stat, dict):
                facts.append(_unresolved("dms", artifact, line, provenance, "invalid_stats_record"))
                continue
            measures = {
                key: number
                for key, raw in {
                    "full_load_rows": stat.get("full_load_rows", stat.get("FullLoadRows")),
                    "cdc_changes": stat.get("cdc_changes", stat.get("CdcChanges")),
                    "latency_seconds": stat.get("latency_seconds", stat.get("CDCLatencySource")),
                    "validation_failures": stat.get("validation_failures", stat.get("ValidationFailedRecords")),
                }.items()
                if (number := _number(raw)) is not None
            }
            facts.append(_fact("dms.stats", artifact, line, provenance, measures=measures, attrs={"schema": stat.get("schema"), "table": stat.get("table"), "status": stat.get("status")}))
    elif stats is not None:
        facts.append(_unresolved("dms", artifact, line, provenance, "missing_task_stats"))
    return facts


def _extract_cdc_events(records: list[tuple[int, Any]], artifact: str, provenance: dict[str, Any]) -> list[Fact]:
    facts: list[Fact] = []
    positions: Counter[str] = Counter()
    transactions: dict[str, dict[str, Any]] = defaultdict(lambda: {"events": 0, "tables": set()})
    snapshots: set[str] = set()
    live_missing_position = False
    for line, record in records:
        if not isinstance(record, dict):
            facts.append(_unresolved("cdc", artifact, line, provenance, "invalid_event_record"))
            continue
        connector = record.get("connector")
        if isinstance(connector, dict):
            attrs = {
                key: item
                for key, item in {
                    "name": _text(connector.get("name", connector.get("connector_name"))),
                    "engine": _text(connector.get("engine", connector.get("source_engine"))),
                    "version": _text(connector.get("version", connector.get("source_version"))),
                }.items()
                if item is not None
            }
            facts.append(
                _fact(
                    "cdc.connector",
                    artifact,
                    line,
                    provenance,
                    attrs=attrs,
                    symbol=attrs.get("name", ""),
                )
            )
            continue
        payload = record.get("payload", record)
        payload = payload if isinstance(payload, dict) else {}
        source = payload.get("source", {})
        source = source if isinstance(source, dict) else {}
        op_raw = _text(payload.get("op", record.get("op")))
        operation = {"c": "CREATE", "r": "READ", "u": "UPDATE", "d": "DELETE", "t": "TRUNCATE"}.get((op_raw or "").lower(), op_raw.upper() if op_raw else None)
        before = payload.get("before")
        after = payload.get("after")
        position = _text(source.get("lsn", source.get("pos", source.get("file_pos", source.get("offset", payload.get("source_position"))))))
        transaction_id = _text(source.get("txId", source.get("txid", payload.get("transaction_id"))))
        table = _text(source.get("table", payload.get("table")))
        key = payload.get("key", record.get("key"))
        key_fields = sorted(key) if isinstance(key, dict) else (["key"] if key is not None else [])
        snapshot = _text(source.get("snapshot", payload.get("snapshot")))
        tombstone = _bool(record.get("tombstone", payload.get("tombstone")))
        attrs = {
            key: item
            for key, item in {
                "operation": operation,
                "source_position": position,
                "transaction_id": transaction_id,
                "table": table,
                "key_fields": key_fields,
                "before_present": before is not None,
                "after_present": after is not None,
                "snapshot": snapshot,
                "tombstone": tombstone,
                "schema_changed": bool(payload.get("schema_change", payload.get("ddl"))),
            }.items()
            if item is not None
        }
        facts.append(_fact("cdc.event", artifact, line, provenance, attrs=attrs, symbol=table or ""))
        if position is None:
            facts.append(_unresolved("cdc", artifact, line, provenance, "missing_source_position", operation=operation))
            if snapshot not in {None, "true", "last"}:
                live_missing_position = True
        else:
            positions[position] += 1
            if positions[position] > 1:
                facts.append(_fact("cdc.duplicate", artifact, line, provenance, measures={"occurrence": positions[position]}, attrs={"source_position": position, "transaction_id": transaction_id, "table": table}))
        if operation in {"CREATE", "READ", "UPDATE", "DELETE"} and not key_fields:
            facts.append(_unresolved("cdc", artifact, line, provenance, "missing_primary_key", operation=operation, table=table))
        if operation == "DELETE" and tombstone is None:
            facts.append(_unresolved("cdc", artifact, line, provenance, "delete_tombstone_behavior", table=table))
        if transaction_id:
            transactions[transaction_id]["events"] += 1
            if table:
                transactions[transaction_id]["tables"].add(table)
        if snapshot:
            snapshots.add(snapshot)
    for snapshot in sorted(snapshots):
        facts.append(_fact("cdc.snapshot", artifact, 1, provenance, attrs={"state": snapshot}))
    for txid, details in sorted(transactions.items()):
        facts.append(_fact("cdc.transaction", artifact, 1, provenance, measures={"event_count": details["events"]}, attrs={"transaction_id": txid, "tables": sorted(details["tables"])}))
    if snapshots and live_missing_position:
        facts.append(_unresolved("cdc", artifact, 1, provenance, "snapshot_cdc_seam"))
    facts.append(_fact("cdc.analyzed", artifact, 1, provenance, attrs={"domain": "cdc", "event_count": len([fact for fact in facts if fact.kind == "cdc.event"])}))
    return facts


def _extract_text(text: str, artifact: str, domain: str) -> list[Fact]:
    provenance = _provenance(text, artifact)
    records, invalid = _records(text, artifact)
    facts: list[Fact] = [_unresolved(domain, artifact, line, provenance, "invalid_json") for line, _ in invalid]
    if domain == "debezium":
        for line, record in records:
            facts.extend(_extract_debezium(record, artifact, line, provenance))
    elif domain == "dms":
        for line, record in records:
            facts.extend(_extract_dms(record, artifact, line, provenance))
    else:
        facts.extend(_extract_cdc_events(records, artifact, provenance))
    if not facts:
        facts.append(_unresolved(domain, artifact, 1, provenance, "empty_artifact"))
    return sort_facts(facts)


def extract_cdc_path(path: str | Path, *, artifact: str = "cdc", repo_root: str | Path | None = None) -> list[Fact]:
    if artifact not in _ARTIFACTS:
        raise ValueError(f"artifact must be one of {sorted(_ARTIFACTS)}")
    target = Path(path)
    return _extract_text(target.read_text(encoding="utf-8"), str(target), artifact)


def extract_cdc_tree(root: str | Path, *, artifact: str = "cdc", repo_root: str | Path | None = None) -> list[Fact]:
    if artifact not in _ARTIFACTS:
        raise ValueError(f"artifact must be one of {sorted(_ARTIFACTS)}")
    base = Path(root)
    facts: list[Fact] = []
    for pattern in ("*.json", "*.jsonl"):
        for target in iter_source_files(base, pattern):
            facts.extend(_extract_text(target.read_text(encoding="utf-8"), str(target), artifact))
    return sort_facts(facts)
