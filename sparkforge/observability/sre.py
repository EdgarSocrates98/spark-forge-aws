"""Offline data observability and SRE evaluation over exported evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class DataObservabilityError(ValueError):
    """Invalid observability evidence or SLO declaration."""


@dataclass(frozen=True, slots=True)
class ObservabilityReport:
    service: str
    slo_reports: tuple[Mapping[str, Any], ...]
    incidents: tuple[Mapping[str, Any], ...]
    dependencies: tuple[Mapping[str, Any], ...]
    blast_radius: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "slo_reports": [dict(item) for item in self.slo_reports],
            "incidents": [dict(item) for item in self.incidents],
            "dependencies": [dict(item) for item in self.dependencies],
            "blast_radius": [dict(item) for item in self.blast_radius],
            "unresolved": [dict(item) for item in self.unresolved],
            "fingerprint": self.fingerprint,
        }


def load_data_observability(path: str | Path) -> ObservabilityReport:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise DataObservabilityError(f"observability artifact not found: {path}")
    try:
        text = target.read_text(encoding="utf-8")
        raw = json.loads(text) if target.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise DataObservabilityError(f"observability artifact unreadable: {path}") from exc
    return _build(raw)


def analyze_data_observability(path: str | Path) -> dict[str, Any]:
    return {"observability": load_data_observability(path).to_dict()}


def _build(raw: object) -> ObservabilityReport:
    if not isinstance(raw, Mapping):
        raise DataObservabilityError("observability root must be an object")
    service = _required(raw.get("service"), "service")
    slos = _list(raw.get("slos", []), "slos")
    measurements = _list(raw.get("measurements", []), "measurements")
    unresolved: list[dict[str, Any]] = _records(raw.get("unresolved", []), "unresolved")
    reports = _evaluate_slos(slos, measurements, unresolved)
    incidents = _incidents(raw.get("incidents", []), unresolved)
    dependencies = _dependencies(raw.get("dependencies", []), unresolved)
    blast_radius = _records(raw.get("blast_radius", []), "blast_radius")
    payload = {
        "service": service,
        "slo_reports": reports,
        "incidents": incidents,
        "dependencies": dependencies,
        "blast_radius": blast_radius,
        "unresolved": _unique(unresolved),
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return ObservabilityReport(service, tuple(reports), tuple(incidents), tuple(dependencies), tuple(blast_radius), tuple(_unique(unresolved)), fingerprint)


def _evaluate_slos(slos: list[dict[str, Any]], measurements: list[dict[str, Any]], unresolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for slo in slos:
        identifier = _required(slo.get("id"), "slo.id")
        objective = slo.get("objective")
        operator = slo.get("operator")
        target = slo.get("target")
        unit = slo.get("unit")
        if not isinstance(objective, (int, float)) or not 0 < objective <= 1:
            unresolved.append({"code": "slo_objective_unresolved", "slo_id": identifier})
        if operator not in {"gte", "lte", "eq"} or not isinstance(target, (int, float)) or not isinstance(unit, str):
            unresolved.append({"code": "slo_target_unresolved", "slo_id": identifier})
        observations = [item for item in measurements if item.get("slo_id") == identifier]
        valid = [item for item in observations if isinstance(item.get("value"), (int, float)) and item.get("unit") == unit]
        if not valid:
            unresolved.append({"code": "slo_measurement_unresolved", "slo_id": identifier, "reason": "no_compatible_observation"})
            result.append({"id": identifier, "indicator": slo.get("indicator", ""), "status": "unresolved", "sample_count": 0})
            continue
        passed = [_compare(float(item["value"]), operator, float(target)) for item in valid]
        good = sum(passed)
        bad_ratio = (len(passed) - good) / len(passed)
        allowed_bad = 1 - float(objective) if isinstance(objective, (int, float)) else None
        consumed = None if not allowed_bad else min(1.0, bad_ratio / allowed_bad)
        result.append(
            {
                "id": identifier,
                "indicator": slo.get("indicator", ""),
                "unit": unit,
                "operator": operator,
                "target": target,
                "objective": objective,
                "sample_count": len(valid),
                "pass_count": good,
                "fail_count": len(passed) - good,
                "compliance": good / len(passed),
                "error_budget_fraction": allowed_bad,
                "error_budget_consumed_fraction": consumed,
                "status": "met" if all(passed) else "breached",
            }
        )
    return sorted(result, key=lambda item: item["id"])


def _incidents(value: object, unresolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    incidents = _list(value, "incidents")
    result: list[dict[str, Any]] = []
    for item in incidents:
        identifier = _required(item.get("id"), "incident.id")
        started = item.get("started_at")
        resolved = item.get("resolved_at")
        report = {**item, "id": identifier, "status": "resolved" if resolved else "open"}
        if isinstance(started, str) and isinstance(resolved, str):
            try:
                report["mttr_seconds"] = (_timestamp(resolved) - _timestamp(started)).total_seconds()
            except ValueError:
                unresolved.append({"code": "incident_timestamp_unresolved", "incident_id": identifier})
        else:
            unresolved.append({"code": "incident_mttr_unresolved", "incident_id": identifier, "reason": "incident_open_or_timestamp_missing"})
        result.append(report)
    return sorted(result, key=lambda item: item["id"])


def _dependencies(value: object, unresolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dependencies = _list(value, "dependencies")
    result: list[dict[str, Any]] = []
    for item in dependencies:
        identifier = _required(item.get("id"), "dependency.id")
        status = item.get("status")
        if status not in {"healthy", "degraded", "down", "unknown"}:
            unresolved.append({"code": "dependency_health_unresolved", "dependency_id": identifier})
        result.append({**item, "id": identifier, "status": status or "unknown"})
    return sorted(result, key=lambda item: item["id"])


def _compare(value: float, operator: object, target: float) -> bool:
    if operator == "gte":
        return value >= target
    if operator == "lte":
        return value <= target
    return value == target


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _list(value: object, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise DataObservabilityError(f"{field} must be a list of objects")
    return [dict(item) for item in value]


def _records(value: object, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    return _list(value, field)


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataObservabilityError(f"{field} must be a non-empty string")
    return value.strip()


def _unique(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {_canonical(item): dict(item) for item in values}
    return [unique[key] for key in sorted(unique)]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


__all__ = ["DataObservabilityError", "ObservabilityReport", "analyze_data_observability", "load_data_observability"]
