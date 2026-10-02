"""Declarative Forge Lab Scenario DSL and action compiler."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .contract import Fidelity, LabContractError, load_resource_contract


ACTION_KINDS = frozenset(
    {
        "seed_dataset",
        "start_workload",
        "capture_baseline",
        "inject_fault",
        "wait_condition",
        "capture_artifacts",
        "analyze",
        "judge",
        "compare_oracle",
        "capture_recovery",
        "cleanup",
        "receipt",
    }
)


@dataclass(frozen=True, slots=True)
class ScenarioAction:
    kind: str
    parameters: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "parameters": _plain(self.parameters)}


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    scenario_id: str
    slug: str
    version: int
    title: str
    resource: Any
    fidelity: Fidelity
    topology: Mapping[str, Any]
    dataset: Mapping[str, Any]
    setup: Mapping[str, Any]
    workload: Mapping[str, Any]
    fault: Mapping[str, Any]
    observe: tuple[str, ...]
    expected: Mapping[str, Any]
    cleanup: Mapping[str, Any]
    experiment_plan: Mapping[str, Any]
    fingerprint: str

    def compile_actions(self) -> tuple[ScenarioAction, ...]:
        """Compile only allowlisted primitives; never emit arbitrary shell."""
        actions = (
            ScenarioAction("seed_dataset", {"dataset": _plain(self.dataset)}),
            ScenarioAction("start_workload", {"workload": _plain(self.workload)}),
            ScenarioAction("capture_baseline", {"observe": list(self.observe)}),
            ScenarioAction("inject_fault", {"fault": _plain(self.fault), "requires_confirmation": True}),
            ScenarioAction("wait_condition", {"condition": _plain(self.fault.get("wait_until", {"status": "changed"}))}),
            ScenarioAction("capture_artifacts", {"paths": list(self.expected.get("artifact_paths", []))}),
            ScenarioAction("analyze", {"analyzers": list(self.expected.get("analyzers", []))}),
            ScenarioAction("judge", {"rules": list(self.expected.get("findings", []))}),
            ScenarioAction("compare_oracle", {"expected": _plain(self.expected)}),
            ScenarioAction("capture_recovery", {"observe": list(self.observe), "phase": "recovery"}),
            ScenarioAction("cleanup", {"cleanup": _plain(self.cleanup)}),
            ScenarioAction("receipt", {"scenario": self.scenario_id}),
        )
        if any(action.kind not in ACTION_KINDS for action in actions):
            raise LabContractError(f"scenario {self.scenario_id} compiled unsupported action")
        return actions

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.scenario_id,
            "slug": self.slug,
            "version": self.version,
            "title": self.title,
            "resource": self.resource.to_dict(),
            "fidelity": self.fidelity.to_dict(),
            "topology": _plain(self.topology),
            "dataset": _plain(self.dataset),
            "setup": _plain(self.setup),
            "workload": _plain(self.workload),
            "fault": _plain(self.fault),
            "observe": list(self.observe),
            "expected": _plain(self.expected),
            "cleanup": _plain(self.cleanup),
            "experiment_plan": _plain(self.experiment_plan),
            "fingerprint": self.fingerprint,
            "actions": [action.to_dict() for action in self.compile_actions()],
        }


@dataclass(frozen=True, slots=True)
class ScenarioSuite:
    schema_version: int
    scenarios: tuple[ScenarioSpec, ...]
    fingerprint: str

    def by_id(self, identifier: str) -> ScenarioSpec:
        for scenario in self.scenarios:
            if identifier in {scenario.scenario_id, scenario.slug}:
                return scenario
        raise LabContractError(f"scenario not found: {identifier}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scenario_count": len(self.scenarios),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "fingerprint": self.fingerprint,
        }


def load_scenario_suite(path: str | Path) -> ScenarioSuite:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise LabContractError(f"scenario suite not found: {path}")
    try:
        text = target.read_text(encoding="utf-8")
        raw = json.loads(text) if target.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise LabContractError(f"scenario suite unreadable: {path}") from exc
    if not isinstance(raw, Mapping) or raw.get("schema_version") != 1:
        raise LabContractError("scenario suite schema_version must be 1")
    entries = raw.get("scenarios")
    if not isinstance(entries, list) or not entries:
        raise LabContractError("scenario suite scenarios must be a non-empty list")
    scenarios = tuple(_build_scenario(item) for item in entries)
    identifiers = [scenario.scenario_id for scenario in scenarios]
    if len(set(identifiers)) != len(identifiers):
        raise LabContractError("scenario suite has duplicate ids")
    payload = [scenario.to_dict() for scenario in scenarios]
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return ScenarioSuite(1, tuple(sorted(scenarios, key=lambda item: item.scenario_id)), fingerprint)


def _build_scenario(raw: object) -> ScenarioSpec:
    if not isinstance(raw, Mapping):
        raise LabContractError("scenario must be an object")
    scenario_id = _required(raw.get("id"), "scenario.id")
    slug = _required(raw.get("slug", scenario_id.lower().replace("_", "-")), f"scenario[{scenario_id}].slug")
    version = raw.get("version")
    if version != 1:
        raise LabContractError(f"scenario {scenario_id} version must be 1")
    fidelity_raw = raw.get("fidelity")
    if not isinstance(fidelity_raw, Mapping):
        raise LabContractError(f"scenario {scenario_id} fidelity is required")
    tier = _required(fidelity_raw.get("tier"), f"scenario[{scenario_id}].fidelity.tier")
    if tier not in {"L0", "L1", "L2", "L3"}:
        raise LabContractError(f"scenario {scenario_id} has unsupported fidelity tier")
    fidelity = Fidelity(
        tier=tier,
        environment=_required(fidelity_raw.get("environment", "local"), "fidelity.environment"),
        implementation=_required(fidelity_raw.get("implementation", "declared"), "fidelity.implementation"),
        proves=_strings(fidelity_raw.get("proves", []), "fidelity.proves"),
        does_not_prove=_strings(fidelity_raw.get("does_not_prove", []), "fidelity.does_not_prove"),
    )
    resource = load_resource_contract(raw.get("profile", {"profile": "core", "mode": "lite"}))
    topology = _mapping(raw.get("topology", {}), "topology")
    dataset = _mapping(raw.get("dataset", {}), "dataset")
    if not isinstance(dataset.get("seed"), int):
        raise LabContractError(f"scenario {scenario_id} dataset.seed must be integer")
    if not isinstance(dataset.get("records"), int) or dataset["records"] <= 0:
        raise LabContractError(f"scenario {scenario_id} dataset.records must be positive")
    setup = _mapping(raw.get("setup", {}), "setup")
    workload = _mapping(raw.get("workload", {}), "workload")
    fault = _mapping(raw.get("fault", {"type": "none"}), "fault")
    observe = _strings(raw.get("observe", []), f"scenario[{scenario_id}].observe")
    expected = _mapping(raw.get("expected", {}), "expected")
    for key in ("facts", "findings", "must_not_find", "unresolved"):
        if key in expected and not isinstance(expected[key], list):
            raise LabContractError(f"scenario {scenario_id} expected.{key} must be a list")
    cleanup = _mapping(raw.get("cleanup", {"preserve_artifacts": True}), "cleanup")
    experiment_plan = _mapping(raw.get("experiment_plan", {}), "experiment_plan")
    if not experiment_plan.get("hypothesis"):
        raise LabContractError(f"scenario {scenario_id} requires experiment_plan.hypothesis")
    payload = {
        "id": scenario_id,
        "slug": slug,
        "version": version,
        "title": raw.get("title", scenario_id),
        "profile": resource.to_dict(),
        "fidelity": fidelity.to_dict(),
        "topology": topology,
        "dataset": dataset,
        "setup": setup,
        "workload": workload,
        "fault": fault,
        "observe": observe,
        "expected": expected,
        "cleanup": cleanup,
        "experiment_plan": experiment_plan,
    }
    fingerprint = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return ScenarioSpec(
        scenario_id=scenario_id,
        slug=slug,
        version=1,
        title=str(raw.get("title", scenario_id)),
        resource=resource,
        fidelity=fidelity,
        topology=topology,
        dataset=dataset,
        setup=setup,
        workload=workload,
        fault=fault,
        observe=observe,
        expected=expected,
        cleanup=cleanup,
        experiment_plan=experiment_plan,
        fingerprint=fingerprint,
    )


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LabContractError(f"{field} must be an object")
    return dict(value)


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise LabContractError(f"{field} must be a list of non-empty strings")
    return tuple(sorted(set(item.strip() for item in value)))


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LabContractError(f"{field} must be a non-empty string")
    return value.strip()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


__all__ = ["ACTION_KINDS", "ScenarioAction", "ScenarioSpec", "ScenarioSuite", "load_scenario_suite"]
