"""Coleta read-only de evidências de streaming na AWS.

O coletor não tenta transformar APIs heterogêneas em um falso estado completo.
Ele grava um contrato único que o extrator ``streaming_integrations`` entende:

* checkpoint Spark: lista limitada de objetos sob um prefixo S3;
* Glue: ``get_job``;
* Kinesis: resumo do stream e shards declarados;
* MSK: ``describe_cluster_v2`` (com fallback para a API antiga);
* DMS: ``describe_replication_tasks`` filtrado por ARN.

Nenhuma chamada escreve na AWS. A escrita local é intencional e fica registrada
no manifesto com SHA-256. Connect, Kafka Streams e OpenLineage não possuem uma
API AWS universal; a ausência fica nomeada para o analyzer, nunca é preenchida
por inferência.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sparkforge_aws.collect.aws import CollectionFailed, _offline_hit, _write_and_register
from sparkforge_aws.collect.base import (
    ArtifactEntry,
    require_boto3,
)

_MAX_OBJECTS = 500
_MAX_SHARDS = 500
_MAX_METRIC_PAGES = 20
_KINESIS_METRICS: tuple[tuple[str, str, str], ...] = (
    ("IncomingBytes", "Sum", "Bytes"),
    ("IncomingRecords", "Sum", "Count"),
    ("GetRecords.IteratorAgeMilliseconds", "Maximum", "Milliseconds"),
    ("ReadProvisionedThroughputExceeded", "Average", "Count"),
    ("WriteProvisionedThroughputExceeded", "Average", "Count"),
)
_SECRET_KEY = re.compile(
    r"(?:secret|password|token|private.?key|access.?key|session.?token|authorization)",
    re.IGNORECASE,
)


def _slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return result.strip("._")[:100] or "streaming"


def streaming_integrations_path(
    *,
    checkpoint_s3_uri: str = "",
    glue_job_name: str = "",
    kinesis_stream_name: str = "",
    msk_cluster_arn: str = "",
    dms_task_arn: str = "",
    metrics_start: str = "",
    metrics_end: str = "",
    metrics_period: int = 60,
) -> str:
    """Caminho determinístico derivado somente dos identificadores declarados."""
    values = [
        f"checkpoint={checkpoint_s3_uri}",
        f"glue={glue_job_name}",
        f"kinesis={kinesis_stream_name}",
        f"msk={msk_cluster_arn}",
        f"dms={dms_task_arn}",
    ]
    subject = _slug("__".join(item for item in values if item.split("=", 1)[1]))
    if metrics_start or metrics_end:
        subject += f"__metrics_{_slug(metrics_start)}_{_slug(metrics_end)}_{metrics_period}"
    return f".sparkforge/artifacts/streaming_integrations/{subject}.json"


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


def _client(boto3: Any, service: str, region_name: str) -> Any:
    return boto3.client(service, region_name=region_name) if region_name else boto3.client(service)


def _s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise CollectionFailed(f"checkpoint S3 URI invalida: {uri!r}; use s3://bucket/prefix")
    return parsed.netloc, parsed.path.lstrip("/")


def _parse_iso(value: str) -> datetime:
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
    *, kinesis_stream_name: str, metrics_start: str, metrics_end: str, metrics_period: int
) -> tuple[datetime, datetime] | None:
    if not metrics_start and not metrics_end:
        return None
    if not kinesis_stream_name:
        raise CollectionFailed("métricas temporais exigem --kinesis-stream")
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


def _checkpoint(client: Any, uri: str, max_objects: int) -> dict[str, Any]:
    bucket, prefix = _s3_uri(uri)
    objects: list[dict[str, Any]] = []
    token: str | None = None
    truncated = False
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        page = client.list_objects_v2(**kwargs)
        for item in page.get("Contents") or []:
            objects.append(
                {
                    "key": item.get("Key", ""),
                    "size": item.get("Size"),
                    "etag": item.get("ETag"),
                    "last_modified": item.get("LastModified").isoformat()
                    if hasattr(item.get("LastModified"), "isoformat")
                    else item.get("LastModified"),
                }
            )
            if len(objects) >= max_objects:
                truncated = True
                break
        if truncated or not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
        if not token:
            truncated = True
            break
    objects.sort(key=lambda item: str(item.get("key", "")))
    return {
        "query_name": Path(prefix.rstrip("/")).name or bucket,
        "path": uri,
        "storage": "s3",
        "object_count": len(objects),
        "objects": objects,
        "truncated": truncated,
        "observations": [],
        "unresolved": [
            "checkpoint listing is metadata only; StreamingQueryProgress history was not present"
        ],
    }


def _kinesis_metrics(
    client: Any,
    stream_name: str,
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
            "namespace": "AWS/Kinesis",
            "dimensions": [{"Name": "StreamName", "Value": stream_name}],
        }
        for name, stat, unit in _KINESIS_METRICS
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
    returned = {str(result.get("Label")) for result in results if result.get("Label")}
    expected = {item["name"] for item in definitions}
    missing = sorted(expected - returned)
    unresolved: list[str] = [f"kinesis_metric_missing:{name}" for name in missing]
    observations: list[dict[str, Any]] = []
    for result in results:
        definition = by_id.get(str(result.get("Id")))
        if definition is None:
            unresolved.append(f"kinesis_metric_unknown_result:{result.get('Id')}")
            continue
        timestamps = result.get("Timestamps") or []
        values = result.get("Values") or []
        if len(timestamps) != len(values):
            unresolved.append(f"kinesis_metric_shape_invalid:{definition['name']}")
            continue
        status = result.get("StatusCode")
        if status not in (None, "Complete"):
            unresolved.append(f"kinesis_metric_status:{definition['name']}:{status}")
        for timestamp, value in zip(timestamps, values, strict=True):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                unresolved.append(f"kinesis_metric_value_invalid:{definition['name']}")
                continue
            observed_at = timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp
            if not isinstance(observed_at, str) or not observed_at:
                unresolved.append(f"kinesis_metric_timestamp_invalid:{definition['name']}")
                continue
            observations.append(
                {
                    "name": definition["name"],
                    "stat": definition["stat"],
                    "unit": definition["unit"],
                    "value": value,
                    "observed_at": observed_at,
                    "stream_name": stream_name,
                }
            )
    return {
        "namespace": "AWS/Kinesis",
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


def _kinesis(
    client: Any,
    stream_name: str,
    max_shards: int,
    *,
    cloudwatch_client: Any | None = None,
    metrics_start: str = "",
    metrics_end: str = "",
    metrics_period: int = 60,
) -> dict[str, Any]:
    summary = _redact(client.describe_stream_summary(StreamName=stream_name))
    shards: list[dict[str, Any]] = []
    token: str | None = None
    truncated = False
    while True:
        kwargs: dict[str, Any] = {"StreamName": stream_name}
        if token:
            kwargs["NextToken"] = token
        page = client.list_shards(**kwargs)
        for shard in page.get("Shards") or []:
            shards.append(_redact(shard))
            if len(shards) >= max_shards:
                truncated = True
                break
        if truncated or not page.get("NextToken"):
            break
        token = page["NextToken"]
    payload = {
        "stream_name": stream_name,
        "summary": summary,
        "shards": shards,
        "shard_count": len(shards),
        "truncated": truncated,
        "unresolved": [],
    }
    if metrics_start and metrics_end:
        if cloudwatch_client is None:
            raise CollectionFailed("cliente CloudWatch ausente para métricas temporais Kinesis")
        payload["metrics"] = _kinesis_metrics(
            cloudwatch_client,
            stream_name,
            start=metrics_start,
            end=metrics_end,
            period=metrics_period,
        )
        payload["unresolved"].extend(payload["metrics"]["unresolved"])
    else:
        payload["unresolved"].append(
            "CloudWatch lag, iterator age and reshard history "
            "require a separate time-window collection"
        )
    return payload


def _msk(client: Any, cluster_arn: str) -> dict[str, Any]:
    try:
        response = client.describe_cluster_v2(ClusterArn=cluster_arn)
        api = "describe_cluster_v2"
    except AttributeError:
        response = client.describe_cluster(ClusterArn=cluster_arn)
        api = "describe_cluster"
    return {
        "cluster_arn": cluster_arn,
        "api": api,
        "cluster": _redact(response),
        "unresolved": [
            "broker throughput, consumer lag and network reachability "
            "require temporal or endpoint evidence"
        ],
    }


def _glue(client: Any, job_name: str) -> dict[str, Any]:
    response = client.get_job(Name=job_name)
    return {
        "job_name": job_name,
        "job": _redact(response.get("Job", response)),
        "unresolved": [
            "job run progress and Glue Real-Time Mode capability "
            "require a run artifact and declared runtime"
        ],
    }


def _dms(client: Any, task_arn: str) -> dict[str, Any]:
    response = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn]}]
    )
    return {
        "task_arn": task_arn,
        "tasks": _redact(response.get("ReplicationTasks", [])),
        "unresolved": [
            "transaction order, CDC lag history and endpoint connectivity "
            "require task statistics or logs"
        ],
    }


def collect_streaming_integrations(
    root: Path,
    *,
    now: str,
    checkpoint_s3_uri: str = "",
    glue_job_name: str = "",
    kinesis_stream_name: str = "",
    msk_cluster_arn: str = "",
    dms_task_arn: str = "",
    region_name: str = "",
    max_objects: int = 500,
    max_shards: int = 500,
    metrics_start: str = "",
    metrics_end: str = "",
    metrics_period: int = 60,
    collect_command: str = "",
) -> ArtifactEntry:
    """Coleta um contrato composto usando apenas APIs de leitura.

    O caminho é conhecido antes da primeira chamada AWS; isso permite o cache
    offline-first e torna repetição com o mesmo conjunto de identificadores um
    no-op verificável.
    """
    identifiers = {
        "checkpoint_s3_uri": checkpoint_s3_uri,
        "glue_job_name": glue_job_name,
        "kinesis_stream_name": kinesis_stream_name,
        "msk_cluster_arn": msk_cluster_arn,
        "dms_task_arn": dms_task_arn,
    }
    if not any(identifiers.values()):
        raise CollectionFailed(
            "informe ao menos uma fonte: --checkpoint-s3-uri, --glue-job, "
            "--kinesis-stream, --msk-cluster-arn ou --dms-task-arn"
        )
    if not 1 <= max_objects <= _MAX_OBJECTS:
        raise ValueError(f"max_objects deve estar entre 1 e {_MAX_OBJECTS}")
    if not 1 <= max_shards <= _MAX_SHARDS:
        raise ValueError(f"max_shards deve estar entre 1 e {_MAX_SHARDS}")
    metrics_window = _validate_metrics_window(
        kinesis_stream_name=kinesis_stream_name,
        metrics_start=metrics_start,
        metrics_end=metrics_end,
        metrics_period=metrics_period,
    )

    rel_path = streaming_integrations_path(
        **identifiers,
        metrics_start=metrics_start,
        metrics_end=metrics_end,
        metrics_period=metrics_period,
    )
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    sections: dict[str, Any] = {}
    if checkpoint_s3_uri:
        sections["checkpoint"] = _checkpoint(
            _client(boto3, "s3", region_name), checkpoint_s3_uri, max_objects
        )
    if glue_job_name:
        sections["glue_streaming"] = _glue(_client(boto3, "glue", region_name), glue_job_name)
    if kinesis_stream_name:
        sections["kinesis"] = _kinesis(
            _client(boto3, "kinesis", region_name),
            kinesis_stream_name,
            max_shards,
            cloudwatch_client=_client(boto3, "cloudwatch", region_name) if metrics_window else None,
            metrics_start=metrics_start,
            metrics_end=metrics_end,
            metrics_period=metrics_period,
        )
    if msk_cluster_arn:
        sections["msk"] = _msk(_client(boto3, "kafka", region_name), msk_cluster_arn)
    if dms_task_arn:
        sections["dms"] = _dms(_client(boto3, "dms", region_name), dms_task_arn)

    contract = {
        "schema_version": 1,
        "collected_at": now,
        "collection": {
            "read_only": True,
            "sections": sorted(sections),
            "unresolved": [
                "Kafka Connect, Kafka Streams and OpenLineage "
                "require their own endpoint or exported artifact"
            ],
        },
        **sections,
    }
    content = (json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="streaming_integrations",
        source="aws-read-only-streaming-apis",
        collect_command=collect_command
        or "sparkforge-aws collect streaming-integrations --repo <repo> --now <ISO8601>",
        now=now,
    )
