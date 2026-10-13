"""Deterministic Forge Lab topology and failure-scenario contract."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FORGE_LAB_COMPONENTS = frozenset(
    {
        "postgres",
        "debezium",
        "kafka",
        "flink",
        "spark",
        "iceberg_rest",
        "polaris",
        "minio",
        "prometheus",
    }
)
FORGE_LAB_SCENARIOS = frozenset(
    {
        "broker_kill",
        "skew",
        "consumer_lag",
        "checkpoint_failure",
        "small_files",
        "schema_evolution",
        "cdc_restart",
    }
)


class ForgeLabError(ValueError):
    """Invalid Forge Lab declaration."""


@dataclass(frozen=True, slots=True)
class ForgeLabSpec:
    """Validated local lab specification; no service is started by this object."""

    name: str
    schema_version: int
    components: tuple[Mapping[str, Any], ...]
    scenarios: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def topology_order(self) -> tuple[str, ...]:
        """Return deterministic dependency order, or declaration order on cycles."""
        ids = tuple(str(item["id"]) for item in self.components)
        dependencies = {
            str(item["id"]): tuple(str(dep) for dep in item.get("depends_on", ()))
            for item in self.components
        }
        indegree = {item: 0 for item in ids}
        followers: dict[str, list[str]] = {item: [] for item in ids}
        for item, deps in dependencies.items():
            for dependency in deps:
                if dependency in indegree:
                    indegree[item] += 1
                    followers[dependency].append(item)
        queue = deque(sorted(item for item, count in indegree.items() if count == 0))
        ordered: list[str] = []
        while queue:
            item = queue.popleft()
            ordered.append(item)
            for follower in sorted(followers[item]):
                indegree[follower] -= 1
                if indegree[follower] == 0:
                    queue.append(follower)
        if len(ordered) != len(ids):
            return tuple(sorted(ids))
        return tuple(ordered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lab": self.name,
            "mode": "offline_spec_only",
            "readiness": "unresolved_until_operator_validates_images_and_runtime",
            "components": [dict(item) for item in self.components],
            "topology_order": list(self.topology_order()),
            "scenarios": [dict(item) for item in self.scenarios],
            "unresolved": [dict(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_forge_lab(path: str | Path) -> ForgeLabSpec:
    """Load a YAML/JSON lab declaration without starting Docker."""
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise ForgeLabError(f"forge lab manifest not found: {path}")
    try:
        text = target.read_text(encoding="utf-8")
        raw = json.loads(text) if target.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ForgeLabError(f"forge lab manifest unreadable: {path}") from exc
    return _build_spec(raw, source=target.as_posix())


def analyze_forge_lab(path: str | Path) -> dict[str, Any]:
    """Return topology and scenario catalog; never executes a failure action."""
    return {"lab": load_forge_lab(path).to_dict()}


def _build_spec(raw: object, *, source: str) -> ForgeLabSpec:
    if not isinstance(raw, Mapping):
        raise ForgeLabError("forge lab root must be an object")
    if raw.get("schema_version", 1) != 1:
        raise ForgeLabError("forge lab schema_version must be 1")
    name = raw.get("lab", raw.get("name"))
    if not isinstance(name, str) or not name.strip():
        raise ForgeLabError("forge lab name must be a non-empty string")
    components = _components(raw.get("components"))
    component_ids = {str(item["id"]) for item in components}
    unresolved: list[dict[str, Any]] = []
    for item in components:
        for dependency in item.get("depends_on", ()):
            if dependency not in component_ids:
                unresolved.append(
                    {
                        "code": "forge_lab_dependency_unresolved",
                        "component": item["id"],
                        "dependency": dependency,
                    }
                )
    scenarios = _scenarios(raw.get("scenarios"), component_ids, unresolved)
    unresolved.extend(_records(raw.get("unresolved", []), "unresolved"))
    payload = {
        "schema_version": 1,
        "lab": name.strip(),
        "components": components,
        "scenarios": scenarios,
        "unresolved": _unique(unresolved),
        "source": source,
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return ForgeLabSpec(
        name=name.strip(),
        schema_version=1,
        components=tuple(components),
        scenarios=tuple(scenarios),
        unresolved=tuple(_unique(unresolved)),
        fingerprint=fingerprint,
    )


def _components(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ForgeLabError("forge lab components must be a non-empty list")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise ForgeLabError("forge lab component must be an object")
        identifier = raw.get("id")
        kind = raw.get("kind")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ForgeLabError(f"invalid or duplicate forge lab component: {identifier!r}")
        if not isinstance(kind, str) or kind not in FORGE_LAB_COMPONENTS:
            raise ForgeLabError(f"unsupported forge lab component kind: {kind!r}")
        dependencies = raw.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise ForgeLabError(f"component {identifier} depends_on must be a list of strings")
        result.append(
            {
                **dict(raw),
                "id": identifier.strip(),
                "kind": kind,
                "depends_on": sorted(set(dependencies)),
            }
        )
        seen.add(identifier)
    return sorted(result, key=lambda item: str(item["id"]))


def _scenarios(
    value: object, component_ids: set[str], unresolved: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ForgeLabError("forge lab scenarios must be a list")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise ForgeLabError("forge lab scenario must be an object")
        identifier = raw.get("id")
        target = raw.get("target")
        if (
            not isinstance(identifier, str)
            or identifier not in FORGE_LAB_SCENARIOS
            or identifier in seen
        ):
            raise ForgeLabError(f"unsupported or duplicate forge lab scenario: {identifier!r}")
        if not isinstance(target, str) or not target.strip():
            raise ForgeLabError(f"scenario {identifier} target must be a non-empty string")
        if target not in component_ids:
            unresolved.append(
                {
                    "code": "forge_lab_scenario_target_unresolved",
                    "scenario": identifier,
                    "target": target,
                }
            )
        evidence = raw.get("expected_evidence", [])
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) and item.strip() for item in evidence
        ):
            raise ForgeLabError(
                f"scenario {identifier} expected_evidence must be non-empty strings"
            )
        action = raw.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ForgeLabError(f"scenario {identifier} action must be a non-empty description")
        result.append(
            {
                **dict(raw),
                "id": identifier,
                "target": target,
                "expected_evidence": list(evidence),
                "requires_confirmation": True,
            }
        )
        seen.add(identifier)
    missing = sorted(FORGE_LAB_SCENARIOS - seen)
    unresolved.extend(
        {"code": "forge_lab_scenario_unresolved", "scenario": item} for item in missing
    )
    return sorted(result, key=lambda item: str(item["id"]))


def _records(value: object, field_name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ForgeLabError(f"{field_name} must be a list of objects")
    return [dict(item) for item in value]


def _unique(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(value): dict(value) for value in values}
    return [unique[key] for key in sorted(unique)]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


__all__ = [
    "FORGE_LAB_COMPONENTS",
    "FORGE_LAB_SCENARIOS",
    "ForgeLabError",
    "ForgeLabSpec",
    "analyze_forge_lab",
    "load_forge_lab",
]
