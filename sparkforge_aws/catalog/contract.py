"""Offline catalog, engine and table-binding topology."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CATALOG_KINDS = frozenset(
    {"glue", "iceberg_rest", "polaris", "s3_tables", "lakeformation", "unity", "nessie"}
)
ENGINE_KINDS = frozenset(
    {
        "spark",
        "flink",
        "trino",
        "athena",
        "duckdb",
        "redshift",
        "clickhouse",
        "pinot",
        "druid",
        "snowflake",
        "bigquery",
    }
)
_SECRET_KEYS = frozenset(
    {"password", "token", "secret", "access_key", "secret_key", "private_key", "credential"}
)


class LakehouseCatalogError(ValueError):
    """Invalid catalog topology or secret-bearing declaration."""


@dataclass(frozen=True, slots=True)
class LakehouseCatalogTopology:
    """Normalized catalog topology with declared, not inferred, capabilities."""

    name: str
    schema_version: int
    catalogs: tuple[Mapping[str, Any], ...]
    engines: tuple[Mapping[str, Any], ...]
    tables: tuple[Mapping[str, Any], ...]
    bindings: tuple[Mapping[str, Any], ...]
    provenance: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "topology": self.name,
            "catalogs": [dict(item) for item in self.catalogs],
            "engines": [dict(item) for item in self.engines],
            "tables": [dict(item) for item in self.tables],
            "bindings": [dict(item) for item in self.bindings],
            "provenance": [dict(item) for item in self.provenance],
            "unresolved": [dict(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_lakehouse_catalog(path: str | Path) -> LakehouseCatalogTopology:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise LakehouseCatalogError(f"lakehouse catalog manifest not found: {path}")
    try:
        text = target.read_text(encoding="utf-8")
        raw = json.loads(text) if target.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise LakehouseCatalogError(f"lakehouse catalog manifest unreadable: {path}") from exc
    return _build(raw)


def analyze_lakehouse_catalog(path: str | Path) -> dict[str, Any]:
    return {"catalog": load_lakehouse_catalog(path).to_dict()}


def _build(raw: object) -> LakehouseCatalogTopology:
    if not isinstance(raw, Mapping):
        raise LakehouseCatalogError("lakehouse catalog root must be an object")
    if raw.get("schema_version", 1) != 1:
        raise LakehouseCatalogError("lakehouse catalog schema_version must be 1")
    name = _required(raw.get("topology", raw.get("catalog_topology")), "topology")
    catalogs = _entities(raw.get("catalogs"), "catalog", "id")
    engines = _entities(raw.get("engines"), "engine", "id")
    tables = _entities(raw.get("tables"), "table", "id")
    bindings = _entities(raw.get("bindings"), "binding", "id")
    unresolved = _records(raw.get("unresolved", []), "unresolved")
    provenance = _records(raw.get("provenance", []), "provenance")
    catalog_ids = {str(item["id"]) for item in catalogs}
    engine_ids = {str(item["id"]) for item in engines}
    table_ids = {str(item["id"]) for item in tables}
    for item in catalogs:
        if item["kind"] not in CATALOG_KINDS:
            unresolved.append(
                {"code": "catalog_kind_unresolved", "catalog_id": item["id"], "kind": item["kind"]}
            )
    for item in engines:
        if item["kind"] not in ENGINE_KINDS:
            unresolved.append(
                {"code": "engine_kind_unresolved", "engine_id": item["id"], "kind": item["kind"]}
            )
    for item in tables:
        catalog_id = item.get("catalog_id")
        if catalog_id not in catalog_ids:
            unresolved.append(
                {
                    "code": "table_catalog_unresolved",
                    "table_id": item["id"],
                    "catalog_id": catalog_id,
                }
            )
    for item in bindings:
        for field, values in (
            ("catalog_id", (item.get("catalog_id"),)),
            ("engine_id", (item.get("engine_id"),)),
        ):
            if values[0] not in (catalog_ids if field == "catalog_id" else engine_ids):
                unresolved.append(
                    {
                        "code": "binding_reference_unresolved",
                        "binding_id": item["id"],
                        "field": field,
                        "value": values[0],
                    }
                )
        for table_id in item.get("table_ids", []):
            if table_id not in table_ids:
                unresolved.append(
                    {
                        "code": "binding_table_unresolved",
                        "binding_id": item["id"],
                        "table_id": table_id,
                    }
                )
    payload = {
        "schema_version": 1,
        "topology": name,
        "catalogs": catalogs,
        "engines": engines,
        "tables": tables,
        "bindings": bindings,
        "provenance": provenance,
        "unresolved": _unique(unresolved),
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return LakehouseCatalogTopology(
        name,
        1,
        tuple(catalogs),
        tuple(engines),
        tuple(tables),
        tuple(bindings),
        tuple(provenance),
        tuple(_unique(unresolved)),
        fingerprint,
    )


def _entities(value: object, label: str, identifier_field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise LakehouseCatalogError(f"{label}s must be a list")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise LakehouseCatalogError(f"{label} must be an object")
        _reject_secrets(raw, label)
        identifier = raw.get(identifier_field)
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise LakehouseCatalogError(f"invalid or duplicate {label}: {identifier!r}")
        normalized = dict(raw)
        normalized[identifier_field] = identifier.strip()
        for key in ("capabilities", "table_ids"):
            if key in normalized:
                if not isinstance(normalized[key], list) or not all(
                    isinstance(item, str) for item in normalized[key]
                ):
                    raise LakehouseCatalogError(f"{label}.{key} must be a list of strings")
                normalized[key] = sorted(set(normalized[key]))
        result.append(normalized)
        seen.add(identifier)
    return sorted(result, key=lambda item: str(item[identifier_field]))


def _reject_secrets(value: object, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in _SECRET_KEYS or any(
                marker in key_text for marker in ("password", "token", "secret")
            ):
                raise LakehouseCatalogError(f"secret-bearing field refused: {path}.{key}")
            _reject_secrets(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_secrets(item, f"{path}[{index}]")


def _records(value: object, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise LakehouseCatalogError(f"{label} must be a list of objects")
    return [dict(item) for item in value]


def _unique(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(item): dict(item) for item in values}
    return [unique[key] for key in sorted(unique)]


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LakehouseCatalogError(f"{field} must be a non-empty string")
    return value.strip()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


__all__ = [
    "CATALOG_KINDS",
    "ENGINE_KINDS",
    "LakehouseCatalogError",
    "LakehouseCatalogTopology",
    "analyze_lakehouse_catalog",
    "load_lakehouse_catalog",
]
