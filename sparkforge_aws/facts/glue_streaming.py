"""Extrai fatos offline de definições AWS Glue Streaming/Real-Time Mode.

O artefato deve ser um dump JSON salvo de uma definição de job ou um contrato
equivalente. O módulo observa configuração; não aplica regras, não consulta AWS
e não transforma campo ausente em zero.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge_aws.facts.scan import iter_source_files
from sparkforge_aws.findings.models import Fact, sort_facts

EXTRACTOR_ID = "glue_streaming@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "glue.streaming.job",
        "glue.streaming.source",
        "glue.streaming.sink",
        "glue.streaming.runtime",
        "glue.streaming.unresolved",
        "glue.streaming.analyzed",
    }
)


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


def _unresolved(artifact: str, line: int, provenance: dict[str, Any], reason: str) -> Fact:
    return _fact("glue.streaming.unresolved", artifact, line, provenance, attrs={"reason": reason})


def _provenance(text: str, artifact: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }


def _number(value: Any) -> int | float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return None


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _numbers(data: dict[str, Any], keys: tuple[str, ...]) -> dict[str, int | float]:
    result: dict[str, int | float] = {}
    for key in keys:
        value = _number(data.get(key))
        if value is not None:
            result[key] = value
    return result


def _endpoint_facts(
    stream: dict[str, Any],
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    *,
    plural_key: str,
    singular_key: str,
    role: str,
    kind: str,
    measure_keys: tuple[str, ...],
) -> list[Fact]:
    """Extract explicit Glue Streaming source/sink records fail-closed."""
    raw = stream.get(plural_key, stream.get(singular_key))
    if raw is None:
        return [_unresolved(artifact, line, provenance, f"{role}_metrics_missing")]
    if isinstance(raw, dict):
        records: list[Any] = [raw]
    elif isinstance(raw, list):
        records = raw
    else:
        return [_unresolved(artifact, line, provenance, f"{plural_key}_not_a_list")]
    if not records:
        return [_unresolved(artifact, line, provenance, f"{role}_metrics_missing")]

    facts: list[Fact] = []
    for record in records:
        if not isinstance(record, dict):
            facts.append(_unresolved(artifact, line, provenance, f"invalid_{role}_record"))
            continue
        attrs = {
            f"{role}_id": _value(record, f"{role}_id", f"{role}Id", "id"),
            "name": _value(record, "name", f"{role}_name", f"{role}Name"),
            "type": _value(record, "type", f"{role}_type", f"{role}Type"),
            "connector": _value(record, "connector", "connector_type", f"{role}_connector"),
            "topic": _value(record, "topic", "topic_name"),
            "stream": _value(record, "stream", "stream_name"),
            "table": _value(record, "table", "table_name"),
            "format": _value(record, "format", "data_format"),
            "region": _value(record, "region", "aws_region"),
            "consumer_group": _value(record, "consumer_group", "consumerGroup"),
            "delivery_semantics": _value(record, "delivery_semantics", "deliverySemantics"),
            "starting_position": _value(record, "starting_position", "startingPosition"),
            "checkpoint_location": _value(record, "checkpoint_location", "checkpointLocation"),
            "enabled": _value(record, "enabled"),
        }
        attrs = {
            key: value
            for key, value in attrs.items()
            if isinstance(value, (str, bool)) and (not isinstance(value, str) or value.strip())
        }
        measures = _numbers(record, measure_keys)
        if attrs or measures:
            facts.append(_fact(kind, artifact, line, provenance, measures=measures, attrs=attrs))
            if not measures:
                facts.append(_unresolved(artifact, line, provenance, f"{role}_metrics_missing"))
        else:
            facts.append(_unresolved(artifact, line, provenance, f"{role}_fields_missing"))
    return facts


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
    return ([(1, value)], [])


def _job_record(data: dict[str, Any]) -> dict[str, Any] | None:
    job = data.get("job", data.get("Job", data))
    return job if isinstance(job, dict) else None


def _extract_record(data: Any, artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    if not isinstance(data, dict):
        return [_unresolved(artifact, line, provenance, "invalid_job_record")]
    job = _job_record(data)
    if job is None:
        return [_unresolved(artifact, line, provenance, "missing_job_record")]

    args = job.get("default_arguments", job.get("DefaultArguments", {}))
    args = args if isinstance(args, dict) else {}
    stream = job.get("stream", job.get("streaming", job.get("rtm", {})))
    stream = stream if isinstance(stream, dict) else {}
    command = job.get("command", job.get("Command", ""))
    if isinstance(command, dict):
        command = command.get("name", command.get("Name", ""))
    glue_version = _text(job.get("glue_version", job.get("GlueVersion")))
    mode_value = stream.get("mode", stream.get("streaming_mode"))
    enabled = args.get("--enable-real-time-mode", args.get("enable_real_time_mode"))
    enabled_bool = _bool(enabled)
    mode = (
        "REAL_TIME"
        if enabled_bool is True or str(mode_value).upper() in {"REAL_TIME", "RTM"}
        else "MICRO_BATCH"
    )
    language = _text(args.get("--job-language", args.get("job_language", stream.get("language"))))
    source_type = _text(stream.get("source_type", stream.get("source")))
    output_mode = _text(stream.get("output_mode"))
    stateful = _bool(stream.get("stateful"))
    foreach_batch = _bool(stream.get("foreach_batch"))
    autoscaling = _bool(stream.get("autoscaling"))
    worker_type = _text(job.get("worker_type", job.get("WorkerType", stream.get("worker_type"))))
    attrs = {
        "name": _text(job.get("name", job.get("Name"))) or "",
        "mode": mode,
        "command": str(command).upper() if command else "",
    }
    for key, value in {
        "glue_version": glue_version,
        "language": language.upper() if language else None,
        "source_type": source_type.upper() if source_type else None,
        "output_mode": output_mode.upper() if output_mode else None,
        "stateful": stateful,
        "foreach_batch": foreach_batch,
        "autoscaling": autoscaling,
        "worker_type": worker_type,
    }.items():
        if value is not None:
            attrs[key] = value
    measures = {
        key: number
        for key, value in {
            "partition_count": stream.get("partition_count"),
            "task_slots": stream.get("task_slots"),
            "worker_count": stream.get(
                "worker_count", job.get("number_of_workers", job.get("NumberOfWorkers"))
            ),
        }.items()
        if (number := _number(value)) is not None
    }
    facts = [
        _fact(
            "glue.streaming.job",
            artifact,
            line,
            provenance,
            measures=measures,
            attrs=attrs,
            symbol=attrs["name"],
        ),
    ]
    facts.extend(
        _endpoint_facts(
            stream,
            artifact,
            line,
            provenance,
            plural_key="sources",
            singular_key="source",
            role="source",
            kind="glue.streaming.source",
            measure_keys=(
                "partition_count",
                "shard_count",
                "lag",
                "lag_records",
                "backlog",
                "backlog_records",
                "num_records_in",
                "num_records_out",
                "records_per_second",
                "batch_duration_ms",
            ),
        )
    )
    facts.extend(
        _endpoint_facts(
            stream,
            artifact,
            line,
            provenance,
            plural_key="sinks",
            singular_key="sink",
            role="sink",
            kind="glue.streaming.sink",
            measure_keys=(
                "num_records_in",
                "num_records_out",
                "pending_commits",
                "commit_duration_ms",
                "commit_failures",
                "write_failures",
                "failed_writes",
                "records_per_second",
                "batch_duration_ms",
            ),
        )
    )
    if glue_version is not None:
        facts.append(
            _fact(
                "glue.streaming.runtime",
                artifact,
                line,
                provenance,
                attrs={"glue_version": glue_version},
            )
        )
    missing = [
        key
        for key, value in {
            "language": language,
            "source_type": source_type,
            "output_mode": output_mode,
            "stateful": stateful,
            "foreach_batch": foreach_batch,
        }.items()
        if value is None
    ]
    if mode == "REAL_TIME" and missing:
        facts.append(_unresolved(artifact, line, provenance, "rtm_constraints"))
    if (
        mode == "REAL_TIME"
        and source_type
        and source_type.upper() == "KAFKA"
        and ("partition_count" not in measures or "task_slots" not in measures)
    ):
        facts.append(_unresolved(artifact, line, provenance, "partition_capacity"))
    facts.append(_fact("glue.streaming.analyzed", artifact, line, provenance, attrs={"mode": mode}))
    return facts


def _extract_text(text: str, artifact: str) -> list[Fact]:
    provenance = _provenance(text, artifact)
    records, invalid = _records(text, artifact)
    facts: list[Fact] = [
        _unresolved(artifact, line, provenance, "invalid_json") for line, _ in invalid
    ]
    for line, record in records:
        facts.extend(_extract_record(record, artifact, line, provenance))
    if not facts:
        facts.append(_unresolved(artifact, 1, provenance, "empty_artifact"))
    return sort_facts(facts)


def extract_glue_streaming_path(
    path: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    target = Path(path)
    rel = str(target.relative_to(repo_root)) if repo_root else str(target)
    return _extract_text(target.read_text(encoding="utf-8"), rel.replace("\\", "/"))


def extract_glue_streaming_tree(
    root: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    base = Path(root)
    facts: list[Fact] = []
    for pattern in ("*.json", "*.jsonl"):
        for target in iter_source_files(base, pattern):
            facts.extend(extract_glue_streaming_path(target, repo_root=repo_root))
    return sort_facts(facts)
