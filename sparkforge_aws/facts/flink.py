"""Extrator offline de artefatos Apache Flink e Managed Flink.

O módulo consome dumps JSON/JSONL já salvos. Não chama Flink, AWS ou
CloudWatch. Os namespaces são deliberadamente separados: capacidade upstream
não prova capacidade do serviço gerenciado.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge_aws.facts.scan import iter_source_files
from sparkforge_aws.findings.models import Fact, sort_facts

EXTRACTOR_ID = "flink_streaming@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "flink.job",
        "flink.operator",
        "flink.source",
        "flink.sink",
        "flink.checkpoint",
        "flink.state",
        "flink.metric",
        "flink.unresolved",
        "flink.analyzed",
        "managed_flink.application",
        "managed_flink.config",
        "managed_flink.connector",
        "managed_flink.metric",
        "managed_flink.unresolved",
        "managed_flink.analyzed",
    }
)

_ARTIFACTS = frozenset({"flink", "managed_flink"})


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


def _provenance(text: str, artifact: str, domain: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
        "domain": domain,
    }


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


def _as_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _numbers(data: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in keys:
        value = _number(data.get(key))
        if value is not None:
            result[key] = value
    return result


def _endpoint_facts(
    data: dict[str, Any],
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
    """Extract explicit Flink source/sink records without filling gaps."""
    raw = data.get(plural_key, data.get(singular_key))
    if raw is None:
        return [_unresolved(artifact, line, provenance, "flink", f"{role}_metrics_missing")]
    if isinstance(raw, dict):
        records: list[Any] = [raw]
    elif isinstance(raw, list):
        records = raw
    else:
        return [_unresolved(artifact, line, provenance, "flink", f"{plural_key}_not_a_list")]
    if not records:
        return [_unresolved(artifact, line, provenance, "flink", f"{role}_metrics_missing")]

    facts: list[Fact] = []
    for record in records:
        if not isinstance(record, dict):
            facts.append(_unresolved(artifact, line, provenance, "flink", f"invalid_{role}_record"))
            continue
        attrs = {
            f"{role}_id": _value(record, f"{role}_id", f"{role}Id", "id"),
            "name": _value(record, "name", f"{role}_name", f"{role}Name"),
            "uid": _value(record, "uid", f"{role}_uid"),
            "type": _value(record, "type", f"{role}_type"),
            "connector": _value(record, "connector", "connector_type", f"{role}_connector"),
            "delivery_semantics": _value(record, "delivery_semantics", "deliverySemantics"),
        }
        attrs = {key: value for key, value in attrs.items() if value is not None}
        measures = _numbers(record, measure_keys)
        if attrs or measures:
            facts.append(_fact(kind, artifact, line, provenance, measures=measures, attrs=attrs))
        else:
            facts.append(_unresolved(artifact, line, provenance, "flink", f"{role}_fields_missing"))
    return facts


def _flink_metric_facts(
    data: dict[str, Any],
    artifact: str,
    line: int,
    provenance: dict[str, Any],
) -> list[Fact]:
    """Extract explicitly timestamped upstream metric observations.

    The top-level ``metrics`` key is opt-in so legacy upstream artifacts keep
    their previous fact set. A complete point needs a name, numeric value and
    textual timestamp; anything else remains a named blind spot instead of a
    partial or fabricated observation.
    """
    if "metrics" not in data:
        return []

    raw = data.get("metrics")
    if raw is None:
        return [_unresolved(artifact, line, provenance, "flink", "metrics_missing")]
    if isinstance(raw, dict):
        if "observations" in raw:
            records = raw.get("observations")
        elif any(key in raw for key in ("name", "metric_name", "metricName")):
            records = [raw]
        else:
            return [
                _unresolved(artifact, line, provenance, "flink", "metrics_observations_missing")
            ]
    elif isinstance(raw, list):
        records = raw
    else:
        return [_unresolved(artifact, line, provenance, "flink", "metrics_not_a_list")]

    if not isinstance(records, list) or not records:
        return [_unresolved(artifact, line, provenance, "flink", "metrics_missing")]

    facts: list[Fact] = []
    reserved = {
        "name",
        "metric_name",
        "metricName",
        "value",
        "metric_value",
        "metricValue",
        "observed_at",
        "observedAt",
        "timestamp",
        "time",
        "unit",
        "stat",
        "statistic",
        "scope",
        "operator_id",
        "operatorId",
    }
    for metric in records:
        if not isinstance(metric, dict):
            facts.append(_unresolved(artifact, line, provenance, "flink", "invalid_metric_record"))
            continue

        name = _value(metric, "name", "metric_name", "metricName")
        if not isinstance(name, str) or not name.strip():
            facts.append(_unresolved(artifact, line, provenance, "flink", "metric_name_missing"))
            continue

        value = _number(_value(metric, "value", "metric_value", "metricValue"))
        if value is None:
            facts.append(_unresolved(artifact, line, provenance, "flink", "metric_value_invalid"))
            continue

        observed_at = _value(metric, "observed_at", "observedAt", "timestamp", "time")
        if observed_at is None:
            facts.append(
                _unresolved(artifact, line, provenance, "flink", "metric_timestamp_missing")
            )
            continue
        if not isinstance(observed_at, str) or not observed_at.strip():
            facts.append(
                _unresolved(artifact, line, provenance, "flink", "metric_timestamp_invalid")
            )
            continue

        metric_name = name.strip()
        attrs: dict[str, Any] = {
            "name": metric_name,
            "observed_at": observed_at,
        }
        unit = _value(metric, "unit")
        stat = _value(metric, "stat", "statistic")
        scope = _value(metric, "scope")
        operator_id = _value(metric, "operator_id", "operatorId")
        if isinstance(unit, str) and unit:
            attrs["unit"] = unit
        if isinstance(stat, str) and stat:
            attrs["stat"] = stat
        if isinstance(scope, str) and scope:
            attrs["scope"] = scope
        if isinstance(operator_id, str) and operator_id:
            attrs["operator_id"] = operator_id

        for key, raw_value in metric.items():
            if key in reserved or raw_value is None or isinstance(raw_value, (dict, list)):
                continue
            if isinstance(raw_value, (str, int, float, bool)):
                attrs[str(key)] = raw_value

        facts.append(
            _fact(
                "flink.metric",
                artifact,
                line,
                provenance,
                measures={"value": value},
                attrs=attrs,
                symbol=metric_name,
            )
        )
    return facts


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


def _flink_record(
    data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]
) -> list[Fact]:
    facts: list[Fact] = []
    job = _as_dict(data.get("job")) or data
    job_attrs = {
        "job_id": _value(job, "job_id", "jobId", "id"),
        "name": _value(job, "name", "job_name", "jobName"),
        "api": _value(job, "api", "api_type", "program"),
        "runtime_version": _value(job, "runtime_version", "flink_version", "version"),
    }
    job_measures = _numbers(
        job,
        ("parallelism", "max_parallelism", "task_slots", "restart_count"),
    )
    if any(value is not None for value in job_attrs.values()) or job_measures:
        facts.append(
            _fact(
                "flink.job",
                artifact,
                line,
                provenance,
                measures=job_measures,
                attrs={key: value for key, value in job_attrs.items() if value is not None},
            )
        )

    facts.extend(
        _endpoint_facts(
            data,
            artifact,
            line,
            provenance,
            plural_key="sources",
            singular_key="source",
            role="source",
            kind="flink.source",
            measure_keys=(
                "parallelism",
                "num_records_in",
                "num_records_out",
                "backlog",
                "backlog_records",
                "lag",
                "lag_records",
                "busy_ms",
                "backpressured_ms",
                "backpressured_ratio",
                "idle_ms",
                "idle_ratio",
            ),
        )
    )
    facts.extend(
        _endpoint_facts(
            data,
            artifact,
            line,
            provenance,
            plural_key="sinks",
            singular_key="sink",
            role="sink",
            kind="flink.sink",
            measure_keys=(
                "parallelism",
                "num_records_in",
                "num_records_out",
                "pending_commits",
                "commit_duration_ms",
                "commit_failures",
                "failed_writes",
                "busy_ms",
                "backpressured_ms",
                "backpressured_ratio",
                "idle_ms",
                "idle_ratio",
            ),
        )
    )

    operators = data.get("operators", data.get("operator"))
    if isinstance(operators, dict):
        operators = [operators]
    if isinstance(operators, list):
        for operator in operators:
            if not isinstance(operator, dict):
                facts.append(
                    _unresolved(artifact, line, provenance, "flink", "invalid_operator_record")
                )
                continue
            attrs = {
                "operator_id": _value(operator, "operator_id", "operatorId", "id"),
                "name": _value(operator, "name", "operator_name", "operatorName"),
                "uid": _value(operator, "uid", "operator_uid"),
                "type": _value(operator, "type", "operator_type"),
            }
            measures = _numbers(
                operator,
                (
                    "parallelism",
                    "busy_ms",
                    "backpressured_ms",
                    "idle_ms",
                    "busy_ratio",
                    "backpressured_ratio",
                    "idle_ratio",
                    "num_records_in",
                    "num_records_out",
                ),
            )
            if not attrs and not measures:
                facts.append(
                    _unresolved(artifact, line, provenance, "flink", "operator_fields_missing")
                )
            else:
                facts.append(
                    _fact(
                        "flink.operator", artifact, line, provenance, measures=measures, attrs=attrs
                    )
                )
    elif operators is not None:
        facts.append(_unresolved(artifact, line, provenance, "flink", "operators_not_a_list"))

    checkpoints = data.get("checkpoints", data.get("checkpoint"))
    if isinstance(checkpoints, dict):
        checkpoints = [checkpoints]
    checkpoint_count = 0
    if isinstance(checkpoints, list):
        for checkpoint in checkpoints:
            if not isinstance(checkpoint, dict):
                facts.append(
                    _unresolved(artifact, line, provenance, "flink", "invalid_checkpoint_record")
                )
                continue
            checkpoint_count += 1
            attrs = {
                "checkpoint_id": _value(checkpoint, "checkpoint_id", "checkpointId", "id"),
                "status": _value(checkpoint, "status", "state"),
                "type": _value(checkpoint, "type", "checkpoint_type"),
                "externalized": _value(checkpoint, "externalized"),
            }
            measures = _numbers(
                checkpoint,
                (
                    "duration_ms",
                    "alignment_ms",
                    "state_size_bytes",
                    "checkpointed_size_bytes",
                    "num_subtasks",
                    "acknowledged_subtasks",
                ),
            )
            facts.append(
                _fact(
                    "flink.checkpoint", artifact, line, provenance, measures=measures, attrs=attrs
                )
            )
    elif checkpoints is not None:
        facts.append(_unresolved(artifact, line, provenance, "flink", "checkpoints_not_a_list"))
    else:
        facts.append(_unresolved(artifact, line, provenance, "flink", "checkpoint_metrics_missing"))

    states = data.get("state", data.get("states"))
    if isinstance(states, dict):
        states = [states]
    if isinstance(states, list):
        for state in states:
            if not isinstance(state, dict):
                facts.append(
                    _unresolved(artifact, line, provenance, "flink", "invalid_state_record")
                )
                continue
            attrs = {
                "backend": _value(state, "backend", "state_backend"),
                "operator_id": _value(state, "operator_id", "operatorId"),
                "ttl": _value(state, "ttl", "ttl_ms"),
            }
            measures = _numbers(
                state, ("size_bytes", "num_entries", "keyed_state_bytes", "operator_state_bytes")
            )
            if attrs or measures:
                facts.append(
                    _fact("flink.state", artifact, line, provenance, measures=measures, attrs=attrs)
                )
            else:
                facts.append(
                    _unresolved(artifact, line, provenance, "flink", "state_fields_missing")
                )
    elif states is not None:
        facts.append(_unresolved(artifact, line, provenance, "flink", "state_not_a_list"))

    facts.extend(_flink_metric_facts(data, artifact, line, provenance))

    if not facts:
        facts.append(_unresolved(artifact, line, provenance, "flink", "missing_shape"))
    facts.append(
        _fact(
            "flink.analyzed",
            artifact,
            line,
            provenance,
            measures={
                "checkpoint_count": checkpoint_count,
                "fact_count": len(facts),
            },
            attrs={"artifact": "flink"},
        )
    )
    return facts


def _managed_record(
    data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]
) -> list[Fact]:
    facts: list[Fact] = []
    application = _as_dict(data.get("application")) or data
    attrs = {
        "application_name": _value(application, "application_name", "applicationName", "name"),
        "application_arn": _value(application, "application_arn", "applicationArn", "arn"),
        "status": _value(application, "status", "state"),
        "runtime_version": _value(
            application, "runtime_version", "flink_version", "runtimeVersion"
        ),
        "application_version_id": _value(
            application, "application_version_id", "applicationVersionId", "version_id"
        ),
        "service_execution_role": _value(
            application, "service_execution_role", "serviceExecutionRole"
        ),
        "application_mode": _value(application, "application_mode", "applicationMode"),
    }
    measures = _numbers(application, ("parallelism", "parallelism_per_kpu", "kpu", "task_slots"))
    if attrs or measures:
        facts.append(
            _fact(
                "managed_flink.application",
                artifact,
                line,
                provenance,
                measures=measures,
                attrs=attrs,
            )
        )
    else:
        facts.append(
            _unresolved(artifact, line, provenance, "managed_flink", "application_fields_missing")
        )

    config = data.get("configuration", data.get("config"))
    if isinstance(config, dict):
        for key, value in sorted(config.items(), key=lambda item: str(item[0])):
            facts.append(
                _fact(
                    "managed_flink.config",
                    artifact,
                    line,
                    provenance,
                    attrs={"key": str(key), "value": value},
                )
            )
    elif config is not None:
        facts.append(
            _unresolved(artifact, line, provenance, "managed_flink", "config_not_an_object")
        )

    connectors = data.get("connectors")
    if isinstance(connectors, list):
        for connector in connectors:
            if isinstance(connector, dict):
                facts.append(
                    _fact(
                        "managed_flink.connector",
                        artifact,
                        line,
                        provenance,
                        attrs={
                            key: value
                            for key, value in connector.items()
                            if not isinstance(value, (dict, list))
                        },
                    )
                )
            else:
                facts.append(
                    _unresolved(
                        artifact, line, provenance, "managed_flink", "invalid_connector_record"
                    )
                )

    metrics = data.get("metrics")
    nested_unresolved: list[Any] = []
    if isinstance(metrics, dict):
        nested_unresolved = metrics.get("unresolved") or []
        observations = metrics.get("observations")
        if isinstance(observations, list):
            metrics = observations
        else:
            facts.append(
                _unresolved(
                    artifact, line, provenance, "managed_flink", "metrics_observations_missing"
                )
            )
            metrics = []
    if isinstance(metrics, list):
        for metric in metrics:
            if not isinstance(metric, dict):
                facts.append(
                    _unresolved(
                        artifact, line, provenance, "managed_flink", "invalid_metric_record"
                    )
                )
                continue
            measures = _numbers(
                metric, ("value", "timestamp", "count", "duration_ms", "backpressured_ms")
            )
            attrs = {
                key: value
                for key, value in metric.items()
                if key not in measures and not isinstance(value, (dict, list))
            }
            facts.append(
                _fact(
                    "managed_flink.metric",
                    artifact,
                    line,
                    provenance,
                    measures=measures,
                    attrs=attrs,
                )
            )
    else:
        facts.append(_unresolved(artifact, line, provenance, "managed_flink", "metrics_missing"))

    declared_unresolved = data.get("unresolved")
    reasons = []
    if isinstance(declared_unresolved, list):
        reasons.extend(declared_unresolved)
    if isinstance(nested_unresolved, list):
        reasons.extend(nested_unresolved)
    seen_reasons: set[str] = set()
    for reason in reasons:
        if isinstance(reason, str) and reason.strip() and reason.strip() not in seen_reasons:
            seen_reasons.add(reason.strip())
            if isinstance(reason, str) and reason.strip():
                facts.append(
                    _unresolved(artifact, line, provenance, "managed_flink", reason.strip())
                )

    facts.append(
        _fact(
            "managed_flink.analyzed",
            artifact,
            line,
            provenance,
            measures={"fact_count": len(facts)},
            attrs={"artifact": "managed_flink"},
        )
    )
    return facts


def extract_flink_text(text: str, artifact_path: str, *, artifact: str) -> list[Fact]:
    if artifact not in _ARTIFACTS:
        raise ValueError(f"unknown Flink artifact: {artifact}")
    provenance = _provenance(text, artifact_path, artifact)
    records, invalid = _records(text, artifact_path)
    facts: list[Fact] = []
    domain = "managed_flink" if artifact == "managed_flink" else "flink"
    for line, reason in invalid:
        facts.append(
            _unresolved(artifact_path, line, provenance, domain, "invalid_json", detail=reason)
        )
    for line, value in records:
        if not isinstance(value, dict):
            facts.append(_unresolved(artifact_path, line, provenance, domain, "record_not_object"))
            continue
        facts.extend(
            _managed_record(value, artifact_path, line, provenance)
            if artifact == "managed_flink"
            else _flink_record(value, artifact_path, line, provenance)
        )
    if not facts:
        facts.append(_unresolved(artifact_path, 1, provenance, domain, "empty_artifact"))
    return sort_facts(facts)


def extract_flink_path(
    path: Path | str, *, artifact: str, repo_root: Path | str | None = None
) -> list[Fact]:
    target = Path(path)
    rel = str(target.relative_to(repo_root)) if repo_root else str(target)
    return extract_flink_text(
        target.read_text(encoding="utf-8-sig"), rel.replace("\\", "/"), artifact=artifact
    )


def extract_flink_tree(
    path: Path | str, *, artifact: str, repo_root: Path | str | None = None
) -> list[Fact]:
    root = Path(path)
    facts: list[Fact] = []
    for pattern in ("*.json", "*.jsonl"):
        for source in iter_source_files(root, pattern):
            facts.extend(extract_flink_path(source, artifact=artifact, repo_root=repo_root))
    return sort_facts(facts)
