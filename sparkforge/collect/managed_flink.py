"""Coleta read-only da descrição de uma aplicação Managed Flink.

O collector usa somente ``kinesisanalyticsv2.describe_application`` com
``IncludeAdditionalDetails=False``. O retorno é normalizado para o contrato
que ``analyze flink --artifact managed_flink`` já consome; código do job,
job-plan, métricas temporais e conectores não observados ficam nomeados como
unresolved, nunca inferidos.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sparkforge.collect.aws import CollectionFailed, _offline_hit, _write_and_register
from sparkforge.collect.base import ArtifactEntry, require_boto3

_SECRET_KEY = re.compile(
    r"(?:secret|password|token|private.?key|access.?key|session.?token|authorization)",
    re.IGNORECASE,
)
_MAX_APPLICATION_NAME = 128
_MAX_METRIC_PAGES = 20
_MANAGED_FLINK_METRICS: tuple[tuple[str, str, str], ...] = (
    ("cpuUtilization", "Average", "Percent"),
    ("heapMemoryUtilization", "Average", "Percent"),
    ("lastCheckpointDuration", "Maximum", "Milliseconds"),
    ("lastCheckpointSize", "Maximum", "Bytes"),
    ("numberOfFailedCheckpoints", "Maximum", "Count"),
)


def _slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return result.strip("._")[:120] or "managed-flink"


def managed_flink_path(
    *,
    application_name: str,
    region_name: str = "",
    metrics_start: str = "",
    metrics_end: str = "",
    metrics_period: int = 60,
) -> str:
    identity = application_name if not region_name else f"{application_name}__{region_name}"
    subject = _slug(identity)
    if metrics_start or metrics_end:
        subject += f"__metrics_{_slug(metrics_start)}_{_slug(metrics_end)}_{metrics_period}"
    return f".sparkforge/artifacts/managed_flink_application/{subject}.json"


def _scalar(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def _pick(data: dict[str, Any], fields: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source, target in fields.items():
        if source not in data or _SECRET_KEY.search(source):
            continue
        value = _scalar(data[source])
        if value is not None:
            result[target] = value
    return result


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "<redacted>" if _SECRET_KEY.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return "<binary omitted>"
    return value


def _configuration(detail: dict[str, Any]) -> dict[str, Any]:
    description = detail.get("ApplicationConfigurationDescription")
    if not isinstance(description, dict):
        return {}
    result: dict[str, Any] = {}
    flink = description.get("FlinkApplicationConfigurationDescription")
    if isinstance(flink, dict):
        checkpoint = flink.get("CheckpointConfigurationDescription")
        if isinstance(checkpoint, dict):
            result.update(
                _pick(
                    checkpoint,
                    {
                        "CheckpointingEnabled": "checkpointing_enabled",
                        "CheckpointInterval": "checkpoint_interval_ms",
                        "MinPauseBetweenCheckpoints": "min_pause_between_checkpoints_ms",
                    },
                )
            )
        monitoring = flink.get("MonitoringConfigurationDescription")
        if isinstance(monitoring, dict):
            result.update(
                _pick(monitoring, {"LogLevel": "log_level", "MetricsLevel": "metrics_level"})
            )
        parallelism = flink.get("ParallelismConfigurationDescription")
        if isinstance(parallelism, dict):
            result.update(
                _pick(
                    parallelism,
                    {
                        "AutoScalingEnabled": "auto_scaling_enabled",
                        "CurrentParallelism": "current_parallelism",
                        "Parallelism": "parallelism",
                        "ParallelismPerKPU": "parallelism_per_kpu",
                    },
                )
            )

    vpcs = description.get("VpcConfigurationDescriptions")
    if isinstance(vpcs, list):
        records = [record for record in vpcs if isinstance(record, dict)]
        result["vpc_configuration_count"] = len(records)
        result["vpc_ids"] = [
            record["VpcId"] for record in records if isinstance(record.get("VpcId"), str)
        ]
        result["subnet_count"] = sum(
            len(record.get("SubnetIds", []))
            for record in records
            if isinstance(record.get("SubnetIds"), list)
        )
        result["security_group_count"] = sum(
            len(record.get("SecurityGroupIds", []))
            for record in records
            if isinstance(record.get("SecurityGroupIds"), list)
        )

    code = description.get("ApplicationCodeConfigurationDescription")
    if isinstance(code, dict):
        result.update(_pick(code, {"CodeContentType": "code_content_type"}))
        content = code.get("CodeContentDescription")
        if isinstance(content, dict):
            result.update(_pick(content, {"CodeMD5": "code_md5", "CodeSize": "code_size"}))
            location = content.get("S3ApplicationCodeLocationDescription")
            if isinstance(location, dict):
                result.update(
                    _pick(location, {"BucketARN": "code_bucket_arn", "FileKey": "code_file_key"})
                )

    encryption = description.get("ApplicationEncryptionConfigurationDescription")
    if isinstance(encryption, dict):
        result.update(
            _pick(encryption, {"KeyType": "encryption_key_type", "KeyId": "encryption_key_id"})
        )
    logging_options = detail.get("CloudWatchLoggingOptionDescriptions")
    if isinstance(logging_options, list):
        result["cloudwatch_logging_option_count"] = sum(
            1 for option in logging_options if isinstance(option, dict)
        )
        result["cloudwatch_log_stream_arns"] = [
            option["LogStreamARN"]
            for option in logging_options
            if isinstance(option, dict) and isinstance(option.get("LogStreamARN"), str)
        ]
    return result


def _parse_iso(value: str) -> Any:
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CollectionFailed(f"janela CloudWatch invalida: {value!r}; use ISO 8601") from exc
    if parsed.tzinfo is None:
        raise CollectionFailed(
            f"janela CloudWatch sem timezone: {value!r}; use ISO 8601 com timezone"
        )
    return parsed


def _validate_metrics_window(
    *, metrics_start: str, metrics_end: str, metrics_period: int
) -> tuple[Any, Any] | None:
    if not metrics_start and not metrics_end:
        return None
    if not metrics_start or not metrics_end:
        raise CollectionFailed("métricas temporais exigem --metrics-start e --metrics-end")
    start = _parse_iso(metrics_start)
    end = _parse_iso(metrics_end)
    if end <= start:
        raise CollectionFailed("janela CloudWatch exige metrics_end posterior a metrics_start")
    if (
        not isinstance(metrics_period, int)
        or isinstance(metrics_period, bool)
        or not 60 <= metrics_period <= 86400
    ):
        raise ValueError("metrics_period deve estar entre 60 e 86400 segundos")
    if metrics_period % 60:
        raise ValueError("metrics_period deve ser múltiplo de 60 segundos")
    return start, end


def _metric_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _metrics(
    client: Any,
    application_name: str,
    *,
    start: str,
    end: str,
    period: int,
) -> dict[str, Any]:
    definitions = [
        {
            "name": name,
            "stat": stat,
            "unit": unit,
            "namespace": "AWS/KinesisAnalytics",
            "dimensions": [{"Name": "Application", "Value": application_name}],
        }
        for name, stat, unit in _MANAGED_FLINK_METRICS
    ]
    queries = [
        {
            "Id": f"m{index}",
            "MetricStat": {
                "Metric": {
                    "Namespace": item["namespace"],
                    "MetricName": item["name"],
                    "Dimensions": item["dimensions"],
                },
                "Period": period,
                "Stat": item["stat"],
                "Unit": item["unit"],
            },
            "Label": item["name"],
            "ReturnData": True,
        }
        for index, item in enumerate(definitions)
    ]
    results: list[dict[str, Any]] = []
    token: str | None = None
    for _ in range(_MAX_METRIC_PAGES):
        kwargs: dict[str, Any] = {
            "MetricDataQueries": queries,
            "StartTime": _parse_iso(start),
            "EndTime": _parse_iso(end),
            "ScanBy": "TimestampAscending",
        }
        if token:
            kwargs["NextToken"] = token
        page = client.get_metric_data(**kwargs)
        results.extend(_redact(page.get("MetricDataResults") or []))
        token = page.get("NextToken")
        if not token:
            break
    else:
        raise CollectionFailed(
            f"`get_metric_data` ainda paginava depois de {_MAX_METRIC_PAGES} páginas; "
            "reduza a janela ou aumente o período para evitar artifact parcial"
        )

    by_id = {
        query["Id"]: definition for query, definition in zip(queries, definitions, strict=True)
    }
    returned: set[str] = set()
    unresolved: list[str] = []
    observations: list[dict[str, Any]] = []
    for result in results:
        definition = by_id.get(str(result.get("Id")))
        if definition is None:
            unresolved.append(f"managed_flink_metric_unknown_result:{result.get('Id')}")
            continue
        name = definition["name"]
        returned.add(name)
        timestamps = result.get("Timestamps") or []
        values = result.get("Values") or []
        if len(timestamps) != len(values):
            unresolved.append(f"managed_flink_metric_shape_invalid:{name}")
            continue
        status = result.get("StatusCode")
        if status not in (None, "Complete"):
            unresolved.append(f"managed_flink_metric_status:{name}:{status}")
        for timestamp, value in zip(timestamps, values, strict=True):
            if not _metric_value(value):
                unresolved.append(f"managed_flink_metric_value_invalid:{name}")
                continue
            observed_at = timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp
            if not isinstance(observed_at, str) or not observed_at:
                unresolved.append(f"managed_flink_metric_timestamp_invalid:{name}")
                continue
            observations.append(
                {
                    "name": name,
                    "stat": definition["stat"],
                    "unit": definition["unit"],
                    "value": value,
                    "observed_at": observed_at,
                    "application_name": application_name,
                }
            )
    expected = {item["name"] for item in definitions}
    missing = sorted(expected - returned)
    unresolved.extend(f"managed_flink_metric_missing:{name}" for name in missing)
    return {
        "namespace": "AWS/KinesisAnalytics",
        "start": start,
        "end": end,
        "period_seconds": period,
        "metric_definitions": definitions,
        "metric_data_results": results,
        "metrics_requested": len(definitions),
        "metrics_returned": len(returned & expected),
        "metrics_missing": missing,
        "observations": observations,
        "unresolved": sorted(set(unresolved)),
    }


def collect_managed_flink(
    root: Path | str,
    *,
    application_name: str,
    now: str,
    region_name: str = "",
    metrics_start: str = "",
    metrics_end: str = "",
    metrics_period: int = 60,
    collect_command: str = "",
) -> ArtifactEntry:
    """Collect and register one Managed Flink application description."""
    application_name = application_name.strip()
    if not application_name:
        raise ValueError("informe --application-name")
    if len(application_name) > _MAX_APPLICATION_NAME:
        raise ValueError(f"application_name deve ter no maximo {_MAX_APPLICATION_NAME} caracteres")

    metrics_window = _validate_metrics_window(
        metrics_start=metrics_start,
        metrics_end=metrics_end,
        metrics_period=metrics_period,
    )
    rel_path = managed_flink_path(
        application_name=application_name,
        region_name=region_name,
        metrics_start=metrics_start,
        metrics_end=metrics_end,
        metrics_period=metrics_period,
    )
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = (
        boto3.client("kinesisanalyticsv2", region_name=region_name)
        if region_name
        else boto3.client("kinesisanalyticsv2")
    )
    response = client.describe_application(
        ApplicationName=application_name,
        IncludeAdditionalDetails=False,
    )
    detail = response.get("ApplicationDetail") if isinstance(response, dict) else None
    if not isinstance(detail, dict):
        raise ValueError("DescribeApplication não retornou ApplicationDetail")

    application = _pick(
        detail,
        {
            "ApplicationName": "application_name",
            "ApplicationARN": "application_arn",
            "ApplicationStatus": "status",
            "RuntimeEnvironment": "runtime_version",
            "ApplicationVersionId": "application_version_id",
            "ServiceExecutionRole": "service_execution_role",
            "ApplicationMode": "application_mode",
            "ApplicationDescription": "description",
            "CreateTimestamp": "created_at",
            "LastUpdateTimestamp": "updated_at",
        },
    )
    unresolved = ["managed_flink_connectors_not_observed"]
    if not _configuration(detail):
        unresolved.append("managed_flink_configuration_not_observed")
    payload: dict[str, Any] = {
        "artifact": "managed_flink",
        "api": "kinesisanalyticsv2.describe_application",
        "application": application,
        "configuration": _configuration(detail),
        "unresolved": unresolved,
        "collection": {
            "read_only": True,
            "api": "DescribeApplication",
            "include_additional_details": False,
            "application_name": application_name,
            "region": region_name or None,
        },
    }
    if metrics_window is None:
        payload["unresolved"].append("managed_flink_metrics_not_observed")
    else:
        cloudwatch = (
            boto3.client("cloudwatch", region_name=region_name)
            if region_name
            else boto3.client("cloudwatch")
        )
        payload["metrics"] = _metrics(
            cloudwatch,
            application_name,
            start=metrics_start,
            end=metrics_end,
            period=metrics_period,
        )
        payload["unresolved"].extend(payload["metrics"]["unresolved"])
    payload["unresolved"] = sorted(set(payload["unresolved"]))
    content = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="managed_flink_application",
        source="aws-managed-flink-describe-application-read-only",
        collect_command=collect_command
        or "sparkforge collect managed-flink --repo <repo> "
        "--application-name <name> --now <ISO8601>",
        now=now,
    )


__all__ = ["collect_managed_flink", "managed_flink_path"]
