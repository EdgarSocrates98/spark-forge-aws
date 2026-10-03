"""Offline inventory for serving, ingestion, AI data and radar integrations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ECOSYSTEM_CATEGORIES = frozenset({"serving", "ingestion", "ai", "radar"})
ECOSYSTEM_KINDS = {
    "serving": frozenset(
        {"trino", "redshift", "clickhouse", "pinot", "druid", "duckdb", "snowflake", "bigquery"}
    ),
    "ingestion": frozenset(
        {
            "airbyte",
            "meltano",
            "kafka_connect",
            "debezium",
            "dms",
            "jdbc",
            "api",
            "sftp",
            "saas",
            "mainframe",
            "sap",
        }
    ),
    "ai": frozenset(
        {
            "feature_store",
            "feast",
            "sagemaker_feature_store",
            "embedding_store",
            "vector_index",
            "unstructured_store",
            "model",
        }
    ),
    "radar": frozenset({"beam", "datahub", "openmetadata"}),
}
RELIABILITY_CONTROLS = frozenset(
    {
        "idempotency",
        "checkpointing",
        "retry",
        "dlq",
        "rate_limit",
        "schema_contract",
        "freshness_slo",
        "recovery",
    }
)


class PlatformEcosystemError(ValueError):
    """Invalid data-platform ecosystem inventory."""


@dataclass(frozen=True, slots=True)
class PlatformEcosystem:
    name: str
    systems: tuple[Mapping[str, Any], ...]
    reliability: tuple[Mapping[str, Any], ...]
    integrations: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem": self.name,
            "systems": [dict(item) for item in self.systems],
            "reliability": [dict(item) for item in self.reliability],
            "integrations": [dict(item) for item in self.integrations],
            "unresolved": [dict(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_platform_ecosystem(path: str | Path) -> PlatformEcosystem:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise PlatformEcosystemError(f"platform ecosystem artifact not found: {path}")
    try:
        text = target.read_text(encoding="utf-8")
        raw = json.loads(text) if target.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise PlatformEcosystemError(f"platform ecosystem artifact unreadable: {path}") from exc
    return _build(raw)


def analyze_platform_ecosystem(path: str | Path) -> dict[str, Any]:
    return {"ecosystem": load_platform_ecosystem(path).to_dict()}


def _build(raw: object) -> PlatformEcosystem:
    if not isinstance(raw, Mapping):
        raise PlatformEcosystemError("platform ecosystem root must be an object")
    name = _required(raw.get("ecosystem", raw.get("name")), "ecosystem")
    systems = _systems(raw.get("systems", []))
    reliability = _records(raw.get("reliability", []), "reliability")
    integrations = _records(raw.get("integrations", []), "integrations")
    unresolved: list[dict[str, Any]] = _records(raw.get("unresolved", []), "unresolved")
    system_ids = {str(item["id"]) for item in systems}
    reliability_ids = {str(item.get("system_id")) for item in reliability}
    for item in systems:
        category = item["category"]
        kind = item["kind"]
        if category not in ECOSYSTEM_CATEGORIES:
            unresolved.append(
                {
                    "code": "ecosystem_category_unresolved",
                    "system_id": item["id"],
                    "category": category,
                }
            )
        elif kind not in ECOSYSTEM_KINDS[category]:
            unresolved.append(
                {"code": "ecosystem_kind_unresolved", "system_id": item["id"], "kind": kind}
            )
        for field in ("owner", "source_ref"):
            if not item.get(field):
                unresolved.append(
                    {
                        "code": "ecosystem_identity_unresolved",
                        "system_id": item["id"],
                        "field": field,
                    }
                )
        if item["id"] not in reliability_ids:
            unresolved.append({"code": "reliability_model_unresolved", "system_id": item["id"]})
    for model in reliability:
        system_id = model.get("system_id")
        if system_id not in system_ids:
            unresolved.append({"code": "reliability_system_unresolved", "system_id": system_id})
        for control in RELIABILITY_CONTROLS:
            if control not in model or model[control] is None:
                unresolved.append(
                    {
                        "code": "reliability_control_unresolved",
                        "system_id": system_id,
                        "control": control,
                    }
                )
    for edge in integrations:
        for field in ("source", "target"):
            if edge.get(field) not in system_ids:
                unresolved.append(
                    {
                        "code": "ecosystem_integration_unresolved",
                        "field": field,
                        "value": edge.get(field),
                    }
                )
        if edge.get("role") == "radar" and edge.get("runtime_dependency") is not False:
            unresolved.append(
                {
                    "code": "radar_dependency_unresolved",
                    "system_id": edge.get("target"),
                    "reason": "radar must remain optional",
                }
            )
    systems.sort(key=lambda item: item["id"])
    reliability.sort(key=lambda item: str(item.get("system_id", "")))
    integrations.sort(
        key=lambda item: (
            str(item.get("source", "")),
            str(item.get("target", "")),
            str(item.get("relation", "")),
        )
    )
    payload = {
        "ecosystem": name,
        "systems": systems,
        "reliability": reliability,
        "integrations": integrations,
        "unresolved": _unique(unresolved),
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return PlatformEcosystem(
        name,
        tuple(systems),
        tuple(reliability),
        tuple(integrations),
        tuple(_unique(unresolved)),
        fingerprint,
    )


def _systems(value: object) -> list[dict[str, Any]]:
    entries = _records(value, "systems")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in entries:
        identifier = _required(item.get("id"), "system.id")
        category = _required(item.get("category"), f"system[{identifier}].category")
        kind = _required(item.get("kind"), f"system[{identifier}].kind")
        if identifier in seen:
            raise PlatformEcosystemError(f"duplicate system: {identifier}")
        result.append({**item, "id": identifier, "category": category, "kind": kind})
        seen.add(identifier)
    return result


def _records(value: object, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise PlatformEcosystemError(f"{field} must be a list of objects")
    return [dict(item) for item in value]


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlatformEcosystemError(f"{field} must be a non-empty string")
    return value.strip()


def _unique(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(item): dict(item) for item in values}
    return [unique[key] for key in sorted(unique)]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


__all__ = [
    "ECOSYSTEM_CATEGORIES",
    "ECOSYSTEM_KINDS",
    "RELIABILITY_CONTROLS",
    "PlatformEcosystem",
    "PlatformEcosystemError",
    "analyze_platform_ecosystem",
    "load_platform_ecosystem",
]
