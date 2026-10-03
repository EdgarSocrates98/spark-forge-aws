"""Extract offline evidence for checkpoints, Kafka integrations and lineage.

The input is a sanitized JSON dump, not a live service connection. The
extractor records declarations and observed series without deciding whether a
runtime is healthy. Missing operational context becomes an unresolved fact.
Secret-like values are never copied to the fact store.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_integrations@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "streaming.checkpoint",
        "kafka.connect",
        "kafka.connect.task",
        "kafka.streams",
        "kafka.streams.state_store",
        "lineage.openlineage",
        "streaming_integrations.unresolved",
        "streaming_integrations.analyzed",
    }
)

_SENSITIVE_TOKENS = (
    "secret",
    "password",
    "token",
    "credential",
    "private_key",
    "access_key",
)

_SERIES = (
    "batch_duration_ms",
    "trigger_interval_ms",
    "backlog",
    "state_rows",
    "watermark_delay_ms",
)


def _subject(artifact: str, symbol: str = "") -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": artifact,
        "line": 1,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(text: str, artifact: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }


def _fact(
    kind: str,
    artifact: str,
    provenance: dict[str, Any],
    *,
    attrs: dict[str, Any] | None = None,
    measures: dict[str, int | float] | None = None,
    symbol: str = "",
) -> Fact:
    return Fact(
        kind=kind,
        subject=_subject(artifact, symbol),
        attrs=attrs or {},
        measures=measures or {},
        provenance=provenance,
    )


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _sensitive_key(key: Any) -> bool:
    normalized = str(key).lower()
    return any(token in normalized for token in _SENSITIVE_TOKENS)


def _safe_attrs(item: dict[str, Any], names: tuple[str, ...]) -> tuple[dict[str, Any], list[str]]:
    attrs: dict[str, Any] = {}
    unresolved: list[str] = []
    for name in names:
        if name not in item:
            continue
        value = item[name]
        if _sensitive_key(name):
            unresolved.append(f"sensitive_field_redacted:{name}")
            continue
        if isinstance(value, (str, bool, int, float)):
            attrs[name] = value
        elif isinstance(value, list) and all(isinstance(entry, str) for entry in value):
            attrs[name] = sorted(value)
        elif isinstance(value, dict) and all(isinstance(key, str) for key in value):
            safe_keys = sorted(key for key in value if not _sensitive_key(key))
            attrs[name] = safe_keys
            if len(safe_keys) != len(value):
                unresolved.append(f"nested_secret_redacted:{name}")
        else:
            unresolved.append(f"field_not_scalar:{name}")
    return attrs, unresolved


def _section(data: dict[str, Any], name: str, aliases: tuple[str, ...] = ()) -> tuple[list[dict[str, Any]], list[str]]:
    key = next((candidate for candidate in (name, *aliases) if candidate in data), None)
    if key is None:
        return [], [f"{name}_declaration_missing"]
    value = data[key]
    if isinstance(value, dict):
        return [value], []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)], [
            f"{name}_item_invalid" for item in value if not isinstance(item, dict)
        ]
    return [], [f"{name}_must_be_object_or_list"]


def _series_measures(item: dict[str, Any]) -> tuple[dict[str, int | float], list[str]]:
    measures: dict[str, int | float] = {}
    unresolved: list[str] = []
    lengths: list[int] = []
    for name in _SERIES:
        value = item.get(name, item.get("metrics", {}).get(name) if isinstance(item.get("metrics"), dict) else None)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        numeric = [number for number in (_number(entry) for entry in values) if number is not None]
        if len(numeric) != len(values) or not numeric:
            unresolved.append(f"checkpoint_series_invalid:{name}")
            continue
        lengths.append(len(numeric))
        measures[f"{name}_first"] = numeric[0]
        measures[f"{name}_last"] = numeric[-1]
        measures[f"{name}_max"] = max(numeric)
        if name == "backlog":
            measures["backlog_non_decreasing"] = int(all(left <= right for left, right in zip(numeric, numeric[1:])))
        if name == "state_rows":
            measures["state_rows_non_decreasing"] = int(all(left <= right for left, right in zip(numeric, numeric[1:])))
    if lengths:
        observation_count = max(lengths)
        measures["observation_count"] = observation_count
        if observation_count < 2:
            unresolved.append("checkpoint_series_insufficient")
    return measures, unresolved


def _checkpoint(data: dict[str, Any], artifact: str, provenance: dict[str, Any]) -> tuple[list[Fact], list[str]]:
    records, unresolved = _section(data, "checkpoint")
    facts: list[Fact] = []
    for index, item in enumerate(records):
        name = _text(item.get("query_name", item.get("name"))) or f"checkpoint_{index}"
        attrs, safe_unresolved = _safe_attrs(
            item,
            (
                "query_name",
                "name",
                "path",
                "storage",
                "state_store",
                "schema_version",
                "restart_strategy",
                "trigger",
                "watermark",
                "stateful",
                "source",
            ),
        )
        unresolved.extend(safe_unresolved)
        missing = [field for field in ("query_name", "path", "storage") if not _text(item.get(field, item.get("name") if field == "query_name" else None))]
        unresolved.extend(f"checkpoint_context_missing:{name}:{field}" for field in missing)
        measures, series_unresolved = _series_measures(item)
        unresolved.extend(f"{reason}:{name}" for reason in series_unresolved)
        trigger_interval = _number(item.get("trigger_interval_ms"))
        if trigger_interval is not None:
            measures["trigger_interval_ms"] = trigger_interval
        if measures.get("batch_duration_ms_max", 0) and trigger_interval is not None:
            measures["batch_duration_exceeds_trigger"] = int(measures["batch_duration_ms_max"] > trigger_interval)
        facts.append(_fact("streaming.checkpoint", artifact, provenance, attrs=attrs, measures=measures, symbol=name))
    return facts, unresolved


def _connect(data: dict[str, Any], artifact: str, provenance: dict[str, Any]) -> tuple[list[Fact], list[str]]:
    records, unresolved = _section(data, "kafka_connect")
    facts: list[Fact] = []
    for index, item in enumerate(records):
        name = _text(item.get("name", item.get("connector"))) or f"connector_{index}"
        attrs, safe_unresolved = _safe_attrs(
            item,
            (
                "name",
                "connector",
                "mode",
                "type",
                "connector_class",
                "status",
                "worker_version",
                "source_system",
                "target_system",
                "converter",
                "transforms",
                "error_handling",
                "dlq_topic",
                "offsets",
                "config",
            ),
        )
        unresolved.extend(safe_unresolved)
        missing = [field for field in ("connector_class", "mode", "status", "tasks", "offsets") if field not in item]
        unresolved.extend(f"kafka_connect_context_missing:{name}:{field}" for field in missing)
        tasks = item.get("tasks", [])
        if isinstance(tasks, list):
            for task_index, task in enumerate(tasks):
                if not isinstance(task, dict):
                    unresolved.append(f"kafka_connect_task_invalid:{name}:{task_index}")
                    continue
                task_attrs, task_unresolved = _safe_attrs(task, ("id", "state", "worker_id", "trace"))
                unresolved.extend(f"{reason}:{name}:{task_index}" for reason in task_unresolved)
                task_attrs["connector"] = name
                facts.append(
                    _fact(
                        "kafka.connect.task",
                        artifact,
                        provenance,
                        attrs=task_attrs,
                        symbol=f"{name}.task.{task_index}",
                    )
                )
        else:
            unresolved.append(f"kafka_connect_tasks_invalid:{name}")
        facts.append(_fact("kafka.connect", artifact, provenance, attrs=attrs, measures={"task_count": len(tasks) if isinstance(tasks, list) else 0}, symbol=name))
    return facts, unresolved


def _streams(data: dict[str, Any], artifact: str, provenance: dict[str, Any]) -> tuple[list[Fact], list[str]]:
    records, unresolved = _section(data, "kafka_streams")
    facts: list[Fact] = []
    for index, item in enumerate(records):
        name = _text(item.get("application_id", item.get("name"))) or f"streams_{index}"
        attrs, safe_unresolved = _safe_attrs(
            item,
            (
                "application_id",
                "name",
                "topology",
                "processing_guarantee",
                "joins",
                "windows",
                "repartition_topics",
                "changelog_topics",
                "interactive_queries",
                "runtime_version",
            ),
        )
        unresolved.extend(safe_unresolved)
        missing = [field for field in ("application_id", "processing_guarantee", "state_stores", "repartition_topics", "changelog_topics") if field not in item]
        unresolved.extend(f"kafka_streams_context_missing:{name}:{field}" for field in missing)
        stores = item.get("state_stores", [])
        if isinstance(stores, list):
            for store_index, store in enumerate(stores):
                if isinstance(store, dict):
                    store_attrs, store_unresolved = _safe_attrs(store, ("name", "type", "persistent", "retention", "changelog_topic"))
                    store_attrs["application_id"] = name
                    unresolved.extend(f"{reason}:{name}:{store_index}" for reason in store_unresolved)
                elif isinstance(store, str):
                    store_attrs = {"name": store, "application_id": name}
                else:
                    unresolved.append(f"kafka_streams_state_store_invalid:{name}:{store_index}")
                    continue
                facts.append(_fact("kafka.streams.state_store", artifact, provenance, attrs=store_attrs, symbol=f"{name}.store.{store_index}"))
        else:
            unresolved.append(f"kafka_streams_state_stores_invalid:{name}")
        facts.append(_fact("kafka.streams", artifact, provenance, attrs=attrs, measures={"state_store_count": len(stores) if isinstance(stores, list) else 0}, symbol=name))
    return facts, unresolved


def _openlineage(data: dict[str, Any], artifact: str, provenance: dict[str, Any]) -> tuple[list[Fact], list[str]]:
    records, unresolved = _section(data, "openlineage", ("lineage",))
    facts: list[Fact] = []
    for index, item in enumerate(records):
        job = item.get("job", {}) if isinstance(item.get("job", {}), dict) else {}
        run = item.get("run", {}) if isinstance(item.get("run", {}), dict) else {}
        declared_job_name = _text(job.get("name"))
        name = declared_job_name or f"openlineage_{index}"
        inputs = item.get("inputs", [])
        outputs = item.get("outputs", [])
        facets = item.get("facets", {})
        attrs = {
            "job_name": name,
            "job_namespace": _text(job.get("namespace")) or "",
            "run_id": _text(run.get("runId", run.get("run_id"))) or "",
            "event_type": _text(item.get("eventType", item.get("event_type"))) or "",
            "producer": _text(item.get("producer")) or "",
            "input_count": len(inputs) if isinstance(inputs, list) else 0,
            "output_count": len(outputs) if isinstance(outputs, list) else 0,
            "facet_names": sorted(facets) if isinstance(facets, dict) else [],
        }
        missing = []
        if not declared_job_name:
            missing.append("job")
        if not attrs["run_id"]:
            missing.append("run")
        if not attrs["event_type"]:
            missing.append("event_type")
        if not isinstance(inputs, list):
            missing.append("inputs")
        if not isinstance(outputs, list):
            missing.append("outputs")
        unresolved.extend(f"openlineage_context_missing:{name}:{field}" for field in missing)
        if isinstance(facets, dict) and any(_sensitive_key(key) for key in facets):
            unresolved.append(f"openlineage_sensitive_facet_redacted:{name}")
        facts.append(_fact("lineage.openlineage", artifact, provenance, attrs=attrs, measures={"input_count": attrs["input_count"], "output_count": attrs["output_count"]}, symbol=name))
    return facts, unresolved


def _extract_text(text: str, artifact: str) -> list[Fact]:
    provenance = _provenance(text, artifact)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [_fact("streaming_integrations.unresolved", artifact, provenance, attrs={"reason": "invalid_json", "domain": "artifact", "line": exc.lineno})]
    if not isinstance(data, dict):
        return [_fact("streaming_integrations.unresolved", artifact, provenance, attrs={"reason": "root_must_be_object", "domain": "artifact"})]
    facts: list[Fact] = []
    reasons: list[str] = []
    for builder in (_checkpoint, _connect, _streams, _openlineage):
        section_facts, section_reasons = builder(data, artifact, provenance)
        facts.extend(section_facts)
        reasons.extend(section_reasons)

    def reason_domain(reason: str) -> str:
        for prefix in ("checkpoint", "kafka_connect", "kafka_streams", "openlineage"):
            if reason.startswith(prefix):
                return prefix
        return "artifact"

    for reason in sorted(set(reasons)):
        facts.append(
            _fact(
                "streaming_integrations.unresolved",
                artifact,
                provenance,
                attrs={"reason": reason, "domain": reason_domain(reason)},
                symbol=reason,
            )
        )
    facts.append(
        _fact(
            "streaming_integrations.analyzed",
            artifact,
            provenance,
            attrs={"sections": sorted(key for key in ("checkpoint", "kafka_connect", "kafka_streams", "openlineage") if key in data)},
            measures={"fact_count": len(facts)},
        )
    )
    return sort_facts(facts)


def extract_streaming_integrations_path(path: str | Path, *, repo_root: str | Path | None = None) -> list[Fact]:
    target = Path(path)
    return _extract_text(target.read_text(encoding="utf-8"), str(target))


def extract_streaming_integrations_tree(root: str | Path, *, repo_root: str | Path | None = None) -> list[Fact]:
    facts: list[Fact] = []
    for pattern in ("*.json", "*.jsonl"):
        for path in iter_source_files(Path(root), pattern):
            facts.extend(_extract_text(path.read_text(encoding="utf-8"), str(path)))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_streaming_integrations_path",
    "extract_streaming_integrations_tree",
]
