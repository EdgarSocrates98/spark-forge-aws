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
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sparkforge.collect.aws import CollectionFailed, _offline_hit, _write_and_register
from sparkforge.collect.base import (
    ArtifactEntry,
    CollectorUnavailable,
    require_boto3,
)

_MAX_OBJECTS = 500
_MAX_SHARDS = 500
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


def _kinesis(client: Any, stream_name: str, max_shards: int) -> dict[str, Any]:
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
    return {
        "stream_name": stream_name,
        "summary": summary,
        "shards": shards,
        "shard_count": len(shards),
        "truncated": truncated,
        "unresolved": [
            "CloudWatch lag, iterator age and reshard history require a separate time-window collection"
        ],
    }


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
            "broker throughput, consumer lag and network reachability require temporal or endpoint evidence"
        ],
    }


def _glue(client: Any, job_name: str) -> dict[str, Any]:
    response = client.get_job(Name=job_name)
    return {
        "job_name": job_name,
        "job": _redact(response.get("Job", response)),
        "unresolved": [
            "job run progress and Glue Real-Time Mode capability require a run artifact and declared runtime"
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
            "transaction order, CDC lag history and endpoint connectivity require task statistics or logs"
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

    rel_path = streaming_integrations_path(**identifiers)
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
            _client(boto3, "kinesis", region_name), kinesis_stream_name, max_shards
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
                "Kafka Connect, Kafka Streams and OpenLineage require their own endpoint or exported artifact"
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
        or "sparkforge collect streaming-integrations --repo <repo> --now <ISO8601>",
        now=now,
    )
