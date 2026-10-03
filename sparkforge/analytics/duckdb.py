"""Read-only DuckDB/Parquet/Iceberg microscope bundle."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class DuckDBMicroscopeError(ValueError):
    """Invalid or mutating DuckDB microscope declaration."""


@dataclass(frozen=True, slots=True)
class DuckDBMicroscope:
    database: str
    objects: tuple[Mapping[str, Any], ...]
    queries: tuple[Mapping[str, Any], ...]
    comparisons: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "database": self.database,
            "read_only": True,
            "objects": [dict(item) for item in self.objects],
            "queries": [dict(item) for item in self.queries],
            "comparisons": [dict(item) for item in self.comparisons],
            "unresolved": [dict(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_duckdb_microscope(path: str | Path) -> DuckDBMicroscope:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise DuckDBMicroscopeError(f"DuckDB microscope bundle not found: {path}")
    try:
        text = target.read_text(encoding="utf-8")
        raw = json.loads(text) if target.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise DuckDBMicroscopeError(f"DuckDB microscope bundle unreadable: {path}") from exc
    return _build(raw)


def analyze_duckdb_microscope(path: str | Path) -> dict[str, Any]:
    return {"duckdb": load_duckdb_microscope(path).to_dict()}


def _build(raw: object) -> DuckDBMicroscope:
    if not isinstance(raw, Mapping):
        raise DuckDBMicroscopeError("DuckDB microscope root must be an object")
    database = raw.get("database")
    if not isinstance(database, str) or not database.strip():
        raise DuckDBMicroscopeError("database must be a non-empty string")
    objects = _objects(raw.get("objects", []))
    queries = _queries(raw.get("queries", []))
    comparisons = _comparisons(raw.get("comparisons", []))
    unresolved = _records(raw.get("unresolved", []), "unresolved")
    payload = {
        "database": database.strip(),
        "objects": objects,
        "queries": queries,
        "comparisons": comparisons,
        "unresolved": _unique(unresolved),
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return DuckDBMicroscope(
        database.strip(),
        tuple(objects),
        tuple(queries),
        tuple(comparisons),
        tuple(_unique(unresolved)),
        fingerprint,
    )


def _objects(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DuckDBMicroscopeError("objects must be a list")
    result: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
            raise DuckDBMicroscopeError("object requires id")
        item = dict(raw)
        item["columns"] = (
            sorted(item.get("columns", []), key=lambda column: str(column.get("name", "")))
            if isinstance(item.get("columns", []), list)
            else []
        )
        result.append(item)
    return sorted(result, key=lambda item: str(item["id"]))


def _queries(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DuckDBMicroscopeError("queries must be a list")
    result: list[dict[str, Any]] = []
    for raw in value:
        if (
            not isinstance(raw, Mapping)
            or not isinstance(raw.get("id"), str)
            or not isinstance(raw.get("sql"), str)
        ):
            raise DuckDBMicroscopeError("query requires id and sql")
        sql = _normalize_sql(raw["sql"])
        if not _read_only(sql):
            raise DuckDBMicroscopeError(f"mutating SQL refused: {raw['id']}")
        result.append({**dict(raw), "sql": sql, "read_only": True})
    return sorted(result, key=lambda item: str(item["id"]))


def _comparisons(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DuckDBMicroscopeError("comparisons must be a list")
    return sorted(
        [dict(item) for item in value if isinstance(item, Mapping)],
        key=lambda item: str(item.get("id", "")),
    )


def _read_only(sql: str) -> bool:
    statement = re.sub(
        r"^\s*(--[^\n]*\n|/\*.*?\*/\s*)*", "", sql, flags=re.DOTALL | re.MULTILINE
    ).lower()
    if re.search(
        r"\b(insert|update|delete|merge|create|drop|alter|copy|install|load|attach|detach)\b",
        statement,
    ):
        return False
    return (
        statement.startswith(
            ("select", "with", "explain", "describe", "show", "summarize", "pragma")
        )
        and "pragma" not in statement[6:]
    )


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().split())


def _records(value: object, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise DuckDBMicroscopeError(f"{label} must be a list of objects")
    return [dict(item) for item in value]


def _unique(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(item): dict(item) for item in values}
    return [unique[key] for key in sorted(unique)]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


__all__ = [
    "DuckDBMicroscope",
    "DuckDBMicroscopeError",
    "analyze_duckdb_microscope",
    "load_duckdb_microscope",
]
