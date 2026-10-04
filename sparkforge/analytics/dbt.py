"""Offline dbt manifest, catalog and run-results topology."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DbtArtifactsError(ValueError):
    """Invalid dbt artifact bundle."""


@dataclass(frozen=True, slots=True)
class DbtArtifacts:
    project: str
    manifest_schema: str
    resources: tuple[Mapping[str, Any], ...]
    catalog_nodes: tuple[Mapping[str, Any], ...]
    run_results: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "manifest_schema": self.manifest_schema,
            "resources": [dict(item) for item in self.resources],
            "catalog_nodes": [dict(item) for item in self.catalog_nodes],
            "run_results": [dict(item) for item in self.run_results],
            "unresolved": [dict(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_dbt_artifacts(path: str | Path) -> DbtArtifacts:
    target = Path(path).expanduser().resolve()
    root = target if target.is_dir() else target.parent
    manifest_path = target / "manifest.json" if target.is_dir() else target
    if not manifest_path.is_file():
        raise DbtArtifactsError(f"dbt manifest.json not found: {path}")
    manifest = _json(manifest_path)
    catalog = _json_optional(root / "catalog.json")
    results = _json_optional(root / "run_results.json")
    return _build(manifest, catalog, results)


def analyze_dbt_artifacts(path: str | Path) -> dict[str, Any]:
    return {"dbt": load_dbt_artifacts(path).to_dict()}


def _build(
    manifest: Mapping[str, Any],
    catalog: Mapping[str, Any] | None,
    results: Mapping[str, Any] | None,
) -> DbtArtifacts:
    raw_resources: list[Mapping[str, Any]] = []
    for group in ("nodes", "sources", "exposures", "metrics", "semantic_models"):
        entries = manifest.get(group, {})
        if isinstance(entries, Mapping):
            raw_resources.extend(item for item in entries.values() if isinstance(item, Mapping))
    resources: list[dict[str, Any]] = []
    known_ids: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    for raw in raw_resources:
        unique_id = raw.get("unique_id")
        if not isinstance(unique_id, str) or not unique_id.strip():
            unresolved.append({"code": "dbt_resource_id_unresolved"})
            continue
        known_ids.add(unique_id)
        depends_on = (
            raw.get("depends_on", {}).get("nodes", [])
            if isinstance(raw.get("depends_on", {}), Mapping)
            else []
        )
        if not isinstance(depends_on, list) or not all(
            isinstance(item, str) for item in depends_on
        ):
            unresolved.append({"code": "dbt_dependencies_unresolved", "unique_id": unique_id})
            depends_on = []
        resources.append(
            {
                "unique_id": unique_id,
                "resource_type": str(raw.get("resource_type", "")),
                "name": str(raw.get("name", unique_id)),
                "package_name": str(raw.get("package_name", "")),
                "relation_name": str(raw.get("relation_name", "")),
                "depends_on": sorted(set(depends_on)),
                "columns": _columns(raw.get("columns", {})),
                "config": _config(raw.get("config", {})),
                "tags": sorted(str(item) for item in raw.get("tags", []) if isinstance(item, str)),
            }
        )
    for item in resources:
        for dependency in item["depends_on"]:
            if dependency not in known_ids:
                unresolved.append(
                    {
                        "code": "dbt_dependency_unresolved",
                        "unique_id": item["unique_id"],
                        "dependency": dependency,
                    }
                )

    catalog_nodes = _catalog_nodes(catalog, unresolved)
    run_results = _run_results(results, unresolved)
    resources.sort(key=lambda item: item["unique_id"])
    payload = {
        "project": str(manifest.get("metadata", {}).get("project_name", ""))
        if isinstance(manifest.get("metadata", {}), Mapping)
        else "",
        "manifest_schema": str(manifest.get("metadata", {}).get("dbt_schema_version", ""))
        if isinstance(manifest.get("metadata", {}), Mapping)
        else "",
        "resources": resources,
        "catalog_nodes": catalog_nodes,
        "run_results": run_results,
        "unresolved": _unique(unresolved),
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return DbtArtifacts(
        payload["project"],
        payload["manifest_schema"],
        tuple(resources),
        tuple(catalog_nodes),
        tuple(run_results),
        tuple(_unique(unresolved)),
        fingerprint,
    )


def _catalog_nodes(
    catalog: Mapping[str, Any] | None, unresolved: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if catalog is None:
        unresolved.append({"code": "dbt_catalog_unresolved", "reason": "catalog_json_missing"})
        return []
    result: list[dict[str, Any]] = []
    for unique_id, raw in (
        catalog.get("nodes", {}) if isinstance(catalog.get("nodes", {}), Mapping) else {}
    ).items():
        if not isinstance(raw, Mapping):
            unresolved.append({"code": "dbt_catalog_node_unresolved", "unique_id": unique_id})
            continue
        result.append(
            {
                "unique_id": str(unique_id),
                "metadata": dict(raw.get("metadata", {}))
                if isinstance(raw.get("metadata", {}), Mapping)
                else {},
                "columns": _columns(raw.get("columns", {})),
            }
        )
    return sorted(result, key=lambda item: item["unique_id"])


def _run_results(
    results: Mapping[str, Any] | None, unresolved: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if results is None:
        unresolved.append(
            {"code": "dbt_run_results_unresolved", "reason": "run_results_json_missing"}
        )
        return []
    values = results.get("results", [])
    if not isinstance(values, list):
        unresolved.append({"code": "dbt_run_results_unresolved", "reason": "results_not_list"})
        return []
    return sorted(
        [
            {
                "unique_id": str(item.get("unique_id", "")),
                "status": str(item.get("status", "")),
                "execution_time": item.get("execution_time"),
                "failures": item.get("failures"),
            }
            for item in values
            if isinstance(item, Mapping)
        ],
        key=lambda item: item["unique_id"],
    )


def _columns(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, Mapping):
        return []
    return sorted(
        [
            {
                "name": str(name),
                "data_type": str(item.get("data_type", item.get("type", ""))),
                "description": str(item.get("description", "")),
            }
            for name, item in value.items()
            if isinstance(item, Mapping)
        ],
        key=lambda item: item["name"],
    )


def _config(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    keys = (
        "materialized",
        "incremental_strategy",
        "on_schema_change",
        "unique_key",
        "schema",
        "alias",
    )
    return {
        key: value[key]
        for key in keys
        if key in value and isinstance(value[key], (str, int, float, bool, list))
    }


def _json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DbtArtifactsError(f"invalid dbt JSON: {path}") from exc
    if not isinstance(value, Mapping):
        raise DbtArtifactsError(f"dbt JSON root must be object: {path}")
    return value


def _json_optional(path: Path) -> Mapping[str, Any] | None:
    return _json(path) if path.is_file() else None


def _unique(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(item): dict(item) for item in values}
    return [unique[key] for key in sorted(unique)]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


__all__ = ["DbtArtifacts", "DbtArtifactsError", "analyze_dbt_artifacts", "load_dbt_artifacts"]
