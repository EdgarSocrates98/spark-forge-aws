"""Offline normalized orchestration inventory."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ORCHESTRATOR_KINDS = frozenset({"airflow", "dagster", "step_functions", "controlm"})


class OrchestrationError(ValueError):
    """Invalid orchestration control-plane artifact."""


@dataclass(frozen=True, slots=True)
class OrchestrationTopology:
    name: str
    orchestrators: tuple[Mapping[str, Any], ...]
    workflows: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology": self.name,
            "orchestrators": [dict(item) for item in self.orchestrators],
            "workflows": [dict(item) for item in self.workflows],
            "unresolved": [dict(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_orchestration(path: str | Path) -> OrchestrationTopology:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise OrchestrationError(f"orchestration artifact not found: {path}")
    try:
        text = target.read_text(encoding="utf-8")
        raw = json.loads(text) if target.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise OrchestrationError(f"orchestration artifact unreadable: {path}") from exc
    return _build(raw)


def analyze_orchestration(path: str | Path) -> dict[str, Any]:
    return {"orchestration": load_orchestration(path).to_dict()}


def _build(raw: object) -> OrchestrationTopology:
    if not isinstance(raw, Mapping):
        raise OrchestrationError("orchestration root must be an object")
    name = _required(raw.get("topology", raw.get("name")), "topology")
    orchestrators = _orchestrators(raw.get("orchestrators", []))
    workflows = _workflows(raw.get("workflows", []))
    unresolved: list[dict[str, Any]] = _records(raw.get("unresolved", []), "unresolved")
    orchestrator_ids = {str(item["id"]) for item in orchestrators}
    workflow_ids = {str(item["id"]) for item in workflows}
    for item in orchestrators:
        if item["kind"] not in ORCHESTRATOR_KINDS:
            unresolved.append(
                {
                    "code": "orchestrator_kind_unresolved",
                    "orchestrator_id": item["id"],
                    "kind": item["kind"],
                }
            )
    for item in workflows:
        if item["orchestrator_id"] not in orchestrator_ids:
            unresolved.append(
                {
                    "code": "workflow_orchestrator_unresolved",
                    "workflow_id": item["id"],
                    "orchestrator_id": item["orchestrator_id"],
                }
            )
        for dependency in item["dependencies"]:
            if dependency not in workflow_ids:
                unresolved.append(
                    {
                        "code": "workflow_dependency_unresolved",
                        "workflow_id": item["id"],
                        "dependency": dependency,
                    }
                )
        for field in ("idempotent", "retry", "concurrency", "backfill"):
            if field not in item or item[field] is None:
                unresolved.append(
                    {
                        "code": "workflow_control_unresolved",
                        "workflow_id": item["id"],
                        "control": field,
                    }
                )
    payload = {
        "topology": name,
        "orchestrators": orchestrators,
        "workflows": workflows,
        "unresolved": _unique(unresolved),
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return OrchestrationTopology(
        name, tuple(orchestrators), tuple(workflows), tuple(_unique(unresolved)), fingerprint
    )


def _orchestrators(value: object) -> list[dict[str, Any]]:
    entries = _records(value, "orchestrators")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in entries:
        identifier = _required(item.get("id"), "orchestrator.id")
        kind = _required(item.get("kind"), f"orchestrator[{identifier}].kind")
        if identifier in seen:
            raise OrchestrationError(f"duplicate orchestrator: {identifier}")
        result.append({**item, "id": identifier, "kind": kind})
        seen.add(identifier)
    return sorted(result, key=lambda item: item["id"])


def _workflows(value: object) -> list[dict[str, Any]]:
    entries = _records(value, "workflows")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in entries:
        identifier = _required(item.get("id"), "workflow.id")
        orchestrator_id = _required(
            item.get("orchestrator_id"), f"workflow[{identifier}].orchestrator_id"
        )
        if identifier in seen:
            raise OrchestrationError(f"duplicate workflow: {identifier}")
        dependencies = item.get("dependencies", [])
        if not isinstance(dependencies, list) or not all(
            isinstance(dep, str) for dep in dependencies
        ):
            raise OrchestrationError(
                f"workflow[{identifier}].dependencies must be a list of strings"
            )
        sensors = item.get("sensors", [])
        if not isinstance(sensors, list) or not all(isinstance(sensor, str) for sensor in sensors):
            raise OrchestrationError(f"workflow[{identifier}].sensors must be a list of strings")
        result.append(
            {
                **item,
                "id": identifier,
                "orchestrator_id": orchestrator_id,
                "dependencies": sorted(set(dependencies)),
                "sensors": sorted(set(sensors)),
            }
        )
        seen.add(identifier)
    return sorted(result, key=lambda item: item["id"])


def _records(value: object, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise OrchestrationError(f"{field} must be a list of objects")
    return [dict(item) for item in value]


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrchestrationError(f"{field} must be a non-empty string")
    return value.strip()


def _unique(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(item): dict(item) for item in values}
    return [unique[key] for key in sorted(unique)]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


__all__ = [
    "ORCHESTRATOR_KINDS",
    "OrchestrationError",
    "OrchestrationTopology",
    "analyze_orchestration",
    "load_orchestration",
]
