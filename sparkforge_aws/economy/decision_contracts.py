"""Versioned YAML contracts for the deterministic shadow Decision Plane."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge_aws.economy.decision_models import BudgetSnapshot
from sparkforge_aws.receipt._hash import digest_of

SCHEMA_VERSION = 1
ALLOWED_MODES = frozenset({"shadow", "assisted", "active"})
ALLOWED_PREDICATES = frozenset(
    {
        "always",
        "cached",
        "deterministic_available",
        "evidence_kind",
        "profile_is",
        "risk_is",
        "task_contains",
    }
)


class ContractError(ValueError):
    """Named invalid-contract error returned by API and CLI adapters."""


@dataclass(frozen=True, slots=True)
class Predicate:
    name: str
    value: Any = True

    def __post_init__(self) -> None:
        if self.name not in ALLOWED_PREDICATES:
            raise ContractError(f"unsupported predicate: {self.name}")


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    route: str
    predicates: tuple[Predicate, ...]
    priority: int = 100

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.route.strip():
            raise ContractError("candidate name and route are required")
        if self.priority < 0:
            raise ContractError("candidate priority must be non-negative")


@dataclass(frozen=True, slots=True)
class Thresholds:
    default_confidence: float
    by_candidate: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        values = (self.default_confidence,) + tuple(value for _, value in self.by_candidate)
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ContractError("confidence thresholds must be between 0 and 1")

    def confidence_for(self, candidate_name: str) -> float:
        return dict(self.by_candidate).get(candidate_name, self.default_confidence)


@dataclass(frozen=True, slots=True)
class DecisionContract:
    schema_version: int
    contract_id: str
    contract_version: str
    mode: str
    candidates: tuple[Candidate, ...]
    thresholds: Thresholds
    budget: BudgetSnapshot
    sha256: str


class ContractRegistry:
    """Loads contracts from a repository-confined directory."""

    def __init__(self, root: Path | str = ".", directory: Path | str | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        self.directory = (
            Path(directory).expanduser().resolve()
            if directory is not None
            else self.root / "config" / "decisions"
        )

    def load(self, contract_id: str, version: str | None = None) -> DecisionContract:
        if not contract_id.strip() or ".." in Path(contract_id).parts:
            raise ContractError("contract_id is invalid")
        path = (self.directory / f"{contract_id}.yaml").resolve()
        if self.directory not in path.parents:
            raise ContractError("contract path escapes decision directory")
        if not path.is_file():
            raise ContractError(f"contract_not_found: {contract_id}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ContractError(f"contract_unreadable: {path}") from exc
        if not isinstance(raw, Mapping):
            raise ContractError("contract must be a mapping")
        contract = self._parse(raw, expected_id=contract_id, source=path)
        if version is not None and contract.contract_version != str(version):
            raise ContractError(
                f"contract_version_mismatch: expected {version}, got {contract.contract_version}"
            )
        return contract

    def _parse(
        self, raw: Mapping[str, Any], *, expected_id: str, source: Path
    ) -> DecisionContract:
        if int(raw.get("schema_version", 0)) != SCHEMA_VERSION:
            raise ContractError(f"unsupported contract schema_version: {source}")
        contract_id = _required_text(raw, "contract_id")
        if contract_id != expected_id:
            raise ContractError(f"contract_id_mismatch: {contract_id}")
        contract_version = _required_text(raw, "contract_version")
        mode = _required_text(raw, "mode")
        if mode not in ALLOWED_MODES:
            raise ContractError(f"unsupported contract mode: {mode}")
        candidates_raw = raw.get("candidates")
        if not isinstance(candidates_raw, list) or not candidates_raw:
            raise ContractError("contract candidates are required")
        candidates = tuple(_candidate(item) for item in candidates_raw)
        if len({candidate.name for candidate in candidates}) != len(candidates):
            raise ContractError("candidate names must be unique")
        budget_raw = raw.get("budget")
        if not isinstance(budget_raw, Mapping):
            raise ContractError("contract budget is required")
        budget = BudgetSnapshot(
            max_total_tokens=_required_nonnegative_int(budget_raw, "max_total_tokens"),
            max_tool_calls=_required_nonnegative_int(budget_raw, "max_tool_calls"),
        )
        thresholds_raw = raw.get("thresholds")
        if not isinstance(thresholds_raw, Mapping):
            raise ContractError("contract thresholds are required")
        default = _number(thresholds_raw.get("default"), "thresholds.default")
        by_candidate_raw = thresholds_raw.get("by_candidate", {})
        if not isinstance(by_candidate_raw, Mapping):
            raise ContractError("thresholds.by_candidate must be a mapping")
        by_candidate = tuple(
            sorted(
                (
                    str(name),
                    _number(value, f"thresholds.by_candidate.{name}"),
                )
                for name, value in by_candidate_raw.items()
            )
        )
        digest_payload = dict(raw)
        digest_payload.pop("sha256", None)
        sha256 = hashlib.sha256(digest_of(digest_payload).encode("ascii")).hexdigest()
        return DecisionContract(
            schema_version=SCHEMA_VERSION,
            contract_id=contract_id,
            contract_version=contract_version,
            mode=mode,
            candidates=candidates,
            thresholds=Thresholds(default, by_candidate),
            budget=budget,
            sha256=sha256,
        )


def _required_text(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, (str, int)) or not str(value).strip():
        raise ContractError(f"contract field required: {key}")
    return str(value).strip()


def _required_nonnegative_int(raw: Mapping[str, Any], key: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool):
        raise ContractError(f"contract budget field required: {key}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"contract budget field required: {key}") from exc
    if number < 0:
        raise ContractError(f"contract budget field must be non-negative: {key}")
    return number


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ContractError(f"{field_name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{field_name} must be numeric") from exc
    if not 0.0 <= number <= 1.0:
        raise ContractError(f"{field_name} must be between 0 and 1")
    return number


def _candidate(raw: Any) -> Candidate:
    if not isinstance(raw, Mapping):
        raise ContractError("candidate must be a mapping")
    name = _required_text(raw, "name")
    route = _required_text(raw, "route")
    priority = raw.get("priority", 100)
    try:
        priority_int = int(priority)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"candidate priority invalid: {name}") from exc
    predicates_raw = raw.get("predicates", [])
    if not isinstance(predicates_raw, list):
        raise ContractError(f"candidate predicates must be a list: {name}")
    predicates = []
    for predicate_raw in predicates_raw:
        if not isinstance(predicate_raw, Mapping):
            raise ContractError(f"candidate predicate must be a mapping: {name}")
        predicate_name = _required_text(predicate_raw, "name")
        predicates.append(Predicate(predicate_name, predicate_raw.get("value", True)))
    return Candidate(name, route, tuple(predicates), priority_int)


__all__ = [
    "ALLOWED_PREDICATES",
    "ContractError",
    "ContractRegistry",
    "DecisionContract",
    "Predicate",
]
