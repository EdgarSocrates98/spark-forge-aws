"""Coleta read-only do AWS Glue Schema Registry.

O módulo só chama operações ``get_*``/``list_*`` do Glue e grava um dump
local consumível por ``analyze schema-registry``. Nenhuma operação de criação,
alteração, registro ou exclusão é chamada. Definição acima do limite não é
truncada: sai como ``unresolved`` no contrato coletado.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from sparkforge.collect.aws import CollectionFailed, _offline_hit, _write_and_register
from sparkforge.collect.base import ArtifactEntry, require_boto3

_MAX_SCHEMAS = 500
_MAX_DEFINITION_BYTES = 170_000
_PAGE_SIZE = 100
_SECRET_KEY = re.compile(r"(?:secret|password|token|private.?key|access.?key|session.?token|authorization)", re.I)


def _slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return result.strip("._")[:120] or "schema-registry"


def schema_registry_path(*, registry_name: str = "", schema_name: str = "", schema_arn: str = "") -> str:
    """Return deterministic artifact path from declared identity only."""
    identity = schema_arn or ":".join(item for item in (registry_name, schema_name) if item)
    return f".sparkforge/artifacts/schema_registry/{_slug(identity)}.json"


def _safe_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _safe_attrs(data: dict[str, Any], fields: dict[str, str]) -> dict[str, Any]:
    """Whitelist AWS response fields and never copy secret-like keys."""
    result: dict[str, Any] = {}
    for source, target in fields.items():
        if source not in data or _SECRET_KEY.search(source):
            continue
        value = data[source]
        if isinstance(value, (str, int, float, bool)) or hasattr(value, "isoformat"):
            result[target] = _safe_value(value)
    return result


def _page(
    client: Any,
    method: str,
    params: dict[str, Any],
    key: str,
    limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Read pages until limit, naming truncation instead of silently dropping."""
    found: list[dict[str, Any]] = []
    token: str | None = None
    truncated = False
    while len(found) < limit:
        request = dict(params)
        request["MaxResults"] = min(_PAGE_SIZE, limit - len(found))
        if token:
            request["NextToken"] = token
        response = getattr(client, method)(**request)
        values = response.get(key) or []
        found.extend(item for item in values if isinstance(item, dict))
        next_token = response.get("NextToken")
        if not next_token:
            break
        token = str(next_token)
        if len(found) >= limit:
            truncated = True
    return found[:limit], truncated


def _definition(value: Any, max_bytes: int) -> tuple[Any | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "schema_definition_missing"
    if len(value.encode("utf-8")) > max_bytes:
        return None, "schema_definition_exceeds_limit"
    try:
        return json.loads(value), None
    except json.JSONDecodeError:
        return value, "schema_definition_not_json"


def _registry(client: Any, registry_name: str) -> dict[str, Any]:
    response = client.get_registry(RegistryId={"RegistryName": registry_name})
    return _safe_attrs(
        response,
        {
            "RegistryName": "name",
            "RegistryArn": "arn",
            "Description": "description",
            "Status": "status",
            "CreatedTime": "created_at",
            "UpdatedTime": "updated_at",
        },
    )


def _schema_record(
    client: Any,
    schema_summary: dict[str, Any],
    *,
    registry: dict[str, Any],
    schema_arn: str,
    max_definition_bytes: int,
    collection_unresolved: list[str],
) -> dict[str, Any]:
    name = str(schema_summary.get("SchemaName") or schema_summary.get("name") or "")
    identity = {"SchemaArn": schema_arn} if schema_arn else {"RegistryName": registry.get("name", ""), "SchemaName": name}
    metadata = client.get_schema(SchemaId=identity)
    schema = _safe_attrs(
        metadata,
        {
            "SchemaName": "name",
            "RegistryName": "registry_name",
            "SchemaArn": "arn",
            "DataFormat": "format",
            "Compatibility": "compatibility",
            "Description": "description",
            "LatestSchemaVersion": "latest_version",
            "NextSchemaVersion": "next_version",
            "SchemaStatus": "status",
            "SchemaCheckpoint": "checkpoint_version",
            "CreatedTime": "created_at",
            "UpdatedTime": "updated_at",
        },
    )
    if "name" not in schema and name:
        schema["name"] = name
    if "registry_name" not in schema and registry.get("name"):
        schema["registry_name"] = registry["name"]

    version_request = {"SchemaId": identity, "SchemaVersionNumber": {"LatestVersion": True}}
    version = client.get_schema_version(**version_request)
    version_attrs = _safe_attrs(
        version,
        {
            "SchemaArn": "schema_arn",
            "SchemaVersionId": "version_id",
            "VersionNumber": "version",
            "Status": "version_status",
            "DataFormat": "version_format",
            "CreatedTime": "version_created_at",
        },
    )
    definition, definition_reason = _definition(version.get("SchemaDefinition"), max_definition_bytes)
    unresolved = list(collection_unresolved)
    if definition is not None:
        schema["definition"] = definition
    if definition_reason:
        unresolved.append(definition_reason)
    if version_attrs.get("version") is not None:
        schema["version"] = version_attrs["version"]
    schema["version_id"] = version_attrs.get("version_id")
    schema["version_status"] = version_attrs.get("version_status")
    schema["version_format"] = version_attrs.get("version_format")
    return {
        "contract": {
            "registry": registry,
            "schema": schema,
        },
        "unresolved": sorted(set(unresolved)),
    }


def collect_schema_registry(
    root: Path | str,
    *,
    now: str,
    registry_name: str = "",
    schema_name: str = "",
    schema_arn: str = "",
    region_name: str = "",
    max_schemas: int = 100,
    max_definition_bytes: int = _MAX_DEFINITION_BYTES,
    collect_command: str = "",
) -> ArtifactEntry:
    """Collect latest schema metadata/definition using read-only Glue APIs."""
    if not registry_name and not schema_arn:
        raise CollectionFailed("informe --registry-name ou --schema-arn")
    if schema_name and not registry_name:
        raise CollectionFailed("--schema-name exige --registry-name")
    if not 1 <= max_schemas <= _MAX_SCHEMAS:
        raise ValueError(f"max_schemas deve estar entre 1 e {_MAX_SCHEMAS}")
    if not 1 <= max_definition_bytes <= _MAX_DEFINITION_BYTES:
        raise ValueError(f"max_definition_bytes deve estar entre 1 e {_MAX_DEFINITION_BYTES}")

    rel_path = schema_registry_path(
        registry_name=registry_name, schema_name=schema_name, schema_arn=schema_arn
    )
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("glue", region_name=region_name) if region_name else boto3.client("glue")
    if schema_arn:
        registry = {"name": registry_name} if registry_name else {}
        summaries = [{"SchemaName": schema_name, "SchemaArn": schema_arn}]
    else:
        registry = _registry(client, registry_name)
        if schema_name:
            summaries = [{"SchemaName": schema_name}]
            truncated = False
        else:
            summaries, truncated = _page(
                client, "list_schemas", {"RegistryName": registry_name}, "Schemas", max_schemas
            )
        if not schema_name and truncated:
            collection_unresolved = ["schema_limit_reached"]
        else:
            collection_unresolved = []
    if schema_arn:
        collection_unresolved = []

    records = [
        _schema_record(
            client,
            summary,
            registry=registry,
            schema_arn=schema_arn or str(summary.get("SchemaArn") or ""),
            max_definition_bytes=max_definition_bytes,
            collection_unresolved=collection_unresolved,
        )
        for summary in summaries[:max_schemas]
    ]
    content = (json.dumps(records, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="schema_registry",
        source="aws-glue-schema-registry-read-only",
        collect_command=collect_command or "sparkforge collect schema-registry --repo <repo> --now <ISO8601>",
        now=now,
    )


__all__ = ["collect_schema_registry", "schema_registry_path"]
