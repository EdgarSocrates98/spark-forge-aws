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

from sparkforge.collect.aws import _offline_hit, _write_and_register
from sparkforge.collect.base import ArtifactEntry, require_boto3

_SECRET_KEY = re.compile(
    r"(?:secret|password|token|private.?key|access.?key|session.?token|authorization)",
    re.IGNORECASE,
)
_MAX_APPLICATION_NAME = 128


def _slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return result.strip("._")[:120] or "managed-flink"


def managed_flink_path(*, application_name: str, region_name: str = "") -> str:
    identity = application_name if not region_name else f"{application_name}__{region_name}"
    return f".sparkforge/artifacts/managed_flink_application/{_slug(identity)}.json"


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
        result["vpc_ids"] = [record["VpcId"] for record in records if isinstance(record.get("VpcId"), str)]
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
                result.update(_pick(location, {"BucketARN": "code_bucket_arn", "FileKey": "code_file_key"}))

    encryption = description.get("ApplicationEncryptionConfigurationDescription")
    if isinstance(encryption, dict):
        result.update(_pick(encryption, {"KeyType": "encryption_key_type", "KeyId": "encryption_key_id"}))
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


def collect_managed_flink(
    root: Path | str,
    *,
    application_name: str,
    now: str,
    region_name: str = "",
    collect_command: str = "",
) -> ArtifactEntry:
    """Collect and register one Managed Flink application description."""
    application_name = application_name.strip()
    if not application_name:
        raise ValueError("informe --application-name")
    if len(application_name) > _MAX_APPLICATION_NAME:
        raise ValueError(f"application_name deve ter no maximo {_MAX_APPLICATION_NAME} caracteres")

    rel_path = managed_flink_path(application_name=application_name, region_name=region_name)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("kinesisanalyticsv2", region_name=region_name) if region_name else boto3.client("kinesisanalyticsv2")
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
    unresolved = [
        "managed_flink_metrics_not_observed",
        "managed_flink_connectors_not_observed",
    ]
    if not _configuration(detail):
        unresolved.append("managed_flink_configuration_not_observed")
    payload = {
        "artifact": "managed_flink",
        "api": "kinesisanalyticsv2.describe_application",
        "application": application,
        "configuration": _configuration(detail),
        "unresolved": sorted(unresolved),
        "collection": {
            "read_only": True,
            "api": "DescribeApplication",
            "include_additional_details": False,
            "application_name": application_name,
            "region": region_name or None,
        },
    }
    content = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="managed_flink_application",
        source="aws-managed-flink-describe-application-read-only",
        collect_command=collect_command or "sparkforge collect managed-flink --repo <repo> --application-name <name> --now <ISO8601>",
        now=now,
    )


__all__ = ["collect_managed_flink", "managed_flink_path"]
