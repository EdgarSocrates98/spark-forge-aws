"""Safe loading and validation of versioned bounded decision contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.decision.models import PrimitiveKind

SCHEMA_VERSION = 1
ALLOWED_MODES = frozenset({"shadow", "active"})
_TOP_LEVEL = frozenset(
    {
        "schema_version",
        "contract_id",
        "contract_version",
        "mode",
        "primitive",
        "state",
        "budget",
        "spec",
        "activation",
        "measurement",
    }
)
_FIELD_TYPES = frozenset({"any", "string", "number", "boolean", "array", "object"})
_SPEC_FIELDS = {
    "choice": frozenset(
        {"options", "select_field", "threshold", "confidence", "confidence_by_option"}
    ),
    "boolean": frozenset({"field"}),
    "gate": frozenset({"requirements", "on_pass"}),
    "score": frozenset({"weights", "threshold", "on_pass"}),
    "route": frozenset({"rules", "default", "default_confidence"}),
    "threshold": frozenset({"field", "operator", "value", "on_pass", "on_fail", "confidence"}),
}
_CONDITION_FIELDS = frozenset({"field", "equals", "in", "contains", "truthy"})


class ContractValidationError(ValueError):
    """Named fail-closed contract validation error."""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    value_type: str = "any"
    order_insensitive: bool = False


@dataclass(frozen=True, slots=True)
class DecisionContract:
    schema_version: int
    contract_id: str
    contract_version: str
    mode: str
    primitive: PrimitiveKind
    state_fields: tuple[FieldSpec, ...]
    spec: dict[str, Any]
    max_input_bytes: int
    cache_max_entries: int
    sha256: str
    activation_enabled: bool = False
    measurement_enabled: bool = True

    def referenced_fields(self) -> tuple[str, ...]:
        fields = [field.name for field in self.state_fields]
        candidate = self.spec.get("field")
        if isinstance(candidate, str) and candidate not in fields:
            fields.append(candidate)
        candidate = self.spec.get("select_field")
        if isinstance(candidate, str) and candidate not in fields:
            fields.append(candidate)
        for rule in self.spec.get("rules", []):
            if isinstance(rule, Mapping):
                for condition in rule.get("when", []):
                    if isinstance(condition, Mapping) and isinstance(condition.get("field"), str):
                        if condition["field"] not in fields:
                            fields.append(condition["field"])
        for item in self.spec.get("requirements", []):
            if isinstance(item, Mapping) and isinstance(item.get("field"), str):
                if item["field"] not in fields:
                    fields.append(item["field"])
        return tuple(fields)


class ContractLoader:
    """Load generic contracts from a repository-confined directory."""

    def __init__(self, root: Path | str = ".", directory: Path | str | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        self.directory = (
            Path(directory).expanduser().resolve()
            if directory is not None
            else self.root / "config" / "decisions"
        )

    def load(self, contract_id: str, version: str | None = None) -> DecisionContract:
        if not contract_id.strip() or ".." in Path(contract_id).parts:
            raise ContractValidationError("contract_id is invalid")
        path = (self.directory / f"{contract_id}.yaml").resolve()
        if self.directory not in path.parents:
            raise ContractValidationError("contract path escapes decision directory")
        if not path.is_file():
            raise ContractValidationError(f"contract_not_found: {contract_id}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ContractValidationError(f"contract_unreadable: {path}") from exc
        return self.parse(raw, expected_id=contract_id, version=version)

    def parse(
        self,
        raw: Mapping[str, Any],
        *,
        expected_id: str | None = None,
        version: str | None = None,
    ) -> DecisionContract:
        if not isinstance(raw, Mapping):
            raise ContractValidationError("contract must be a mapping")
        unknown = sorted(set(raw) - _TOP_LEVEL)
        if unknown:
            raise ContractValidationError(f"unknown contract fields: {', '.join(unknown)}")
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise ContractValidationError("unsupported contract schema_version")
        contract_id = _required_text(raw, "contract_id")
        if expected_id is not None and contract_id != expected_id:
            raise ContractValidationError(f"contract_id_mismatch: {contract_id}")
        contract_version = _required_text(raw, "contract_version")
        if version is not None and contract_version != str(version):
            raise ContractValidationError(
                f"contract_version_mismatch: expected {version}, got {contract_version}"
            )
        mode = _required_text(raw, "mode")
        if mode not in ALLOWED_MODES:
            raise ContractValidationError(f"unsupported contract mode: {mode}")
        try:
            primitive = PrimitiveKind(_required_text(raw, "primitive"))
        except ValueError as exc:
            raise ContractValidationError(f"unknown primitive: {raw.get('primitive')}") from exc
        state_fields = _parse_state_fields(raw.get("state", {}))
        budget = raw.get("budget", {})
        if not isinstance(budget, Mapping):
            raise ContractValidationError("contract budget must be a mapping")
        _reject_unknown(budget, {"max_input_bytes", "cache_max_entries"}, "budget")
        max_input_bytes = _positive_int(
            budget.get("max_input_bytes", 6000), "budget.max_input_bytes"
        )
        cache_max_entries = _positive_int(
            budget.get("cache_max_entries", 128), "budget.cache_max_entries"
        )
        spec = raw.get("spec")
        if not isinstance(spec, Mapping):
            raise ContractValidationError("contract spec is required")
        normalized_spec = _validate_spec(primitive, dict(spec))
        activation = raw.get("activation", {})
        measurement = raw.get("measurement", {})
        if not isinstance(activation, Mapping) or not isinstance(measurement, Mapping):
            raise ContractValidationError("activation and measurement must be mappings")
        _reject_unknown(activation, {"enabled"}, "activation")
        _reject_unknown(measurement, {"enabled"}, "measurement")
        digest_payload = dict(raw)
        digest_payload.pop("sha256", None)
        encoded = json.dumps(
            digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return DecisionContract(
            SCHEMA_VERSION,
            contract_id,
            contract_version,
            mode,
            primitive,
            state_fields,
            normalized_spec,
            max_input_bytes,
            cache_max_entries,
            digest,
            bool(activation.get("enabled", False)),
            bool(measurement.get("enabled", True)),
        )


def _required_text(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, (str, int)) or not str(value).strip():
        raise ContractValidationError(f"contract field required: {key}")
    return str(value).strip()


def _positive_int(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise ContractValidationError(f"{key} must be a positive integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractValidationError(f"{key} must be a positive integer") from exc
    if number < 1:
        raise ContractValidationError(f"{key} must be a positive integer")
    return number


def _parse_state_fields(raw: Any) -> tuple[FieldSpec, ...]:
    if not isinstance(raw, Mapping):
        raise ContractValidationError("contract state must be a mapping")
    _reject_unknown(raw, {"required"}, "state")
    required = raw.get("required", [])
    if not isinstance(required, list):
        raise ContractValidationError("state.required must be a list")
    fields: list[FieldSpec] = []
    for item in required:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, Mapping):
            raise ContractValidationError("state.required entries must be mappings")
        _reject_unknown(item, {"name", "type", "order_insensitive"}, "state field")
        name = str(item.get("name", "")).strip()
        value_type = str(item.get("type", "any"))
        if not name:
            raise ContractValidationError("state field name is required")
        if value_type not in _FIELD_TYPES:
            raise ContractValidationError(f"unsupported state field type: {value_type}")
        fields.append(FieldSpec(name, value_type, bool(item.get("order_insensitive", False))))
    if len({field.name for field in fields}) != len(fields):
        raise ContractValidationError("state field names must be unique")
    return tuple(fields)


def _validate_spec(kind: PrimitiveKind, spec: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(spec, _SPEC_FIELDS[kind.value], f"{kind.value} spec")
    if kind is PrimitiveKind.CHOICE:
        options = spec.get("options")
        if (
            not isinstance(options, list)
            or not options
            or any(not str(item).strip() for item in options)
        ):
            raise ContractValidationError("choice.options must be a non-empty list")
        if len({str(item) for item in options}) != len(options):
            raise ContractValidationError("choice.options must be unique")
        _threshold(spec.get("threshold", 0.0), "choice.threshold")
    elif kind is PrimitiveKind.BOOLEAN:
        _required_spec_text(spec, "field")
    elif kind is PrimitiveKind.GATE:
        requirements = spec.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            raise ContractValidationError("gate.requirements must be a non-empty list")
        for requirement in requirements:
            if (
                not isinstance(requirement, Mapping)
                or not str(requirement.get("field", "")).strip()
            ):
                raise ContractValidationError("gate requirements need a field")
    elif kind is PrimitiveKind.SCORE:
        weights = spec.get("weights")
        if not isinstance(weights, Mapping) or not weights:
            raise ContractValidationError("score.weights must be a non-empty mapping")
        if any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            for value in weights.values()
        ):
            raise ContractValidationError("score weights must be numeric")
        _threshold(spec.get("threshold", 0.0), "score.threshold")
    elif kind is PrimitiveKind.ROUTE:
        rules = spec.get("rules")
        if not isinstance(rules, list) or not rules:
            raise ContractValidationError("route.rules must be a non-empty list")
        routes: set[str] = set()
        for rule in rules:
            if (
                not isinstance(rule, Mapping)
                or not str(rule.get("route", rule.get("target", ""))).strip()
            ):
                raise ContractValidationError("route rules need a route")
            route = str(rule.get("route", rule.get("target"))).strip()
            if route in routes:
                raise ContractValidationError("route values must be unique")
            routes.add(route)
            conditions = rule.get("when", [])
            if not isinstance(conditions, list):
                raise ContractValidationError("route rule when must be a list")
            _reject_unknown(
                rule,
                {"when", "route", "target", "confidence", "threshold", "priority"},
                "route rule",
            )
            for condition in conditions:
                if not isinstance(condition, Mapping):
                    raise ContractValidationError("route conditions must be mappings")
                _reject_unknown(condition, _CONDITION_FIELDS, "route condition")
    elif kind is PrimitiveKind.THRESHOLD:
        _required_spec_text(spec, "field")
        operator = str(spec.get("operator", ""))
        if operator not in {"gt", "gte", "lt", "lte", "eq"}:
            raise ContractValidationError("threshold.operator is invalid")
        if "value" not in spec:
            raise ContractValidationError("threshold.value is required")
        if not str(spec.get("on_pass", "")).strip():
            raise ContractValidationError("threshold.on_pass is required")
    return spec


def _required_spec_text(spec: Mapping[str, Any], key: str) -> str:
    value = spec.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"spec.{key} is required")
    return value.strip()


def _reject_unknown(raw: Mapping[str, Any], allowed: set[str] | frozenset[str], label: str) -> None:
    unknown = sorted(set(raw) - set(allowed))
    if unknown:
        raise ContractValidationError(f"unknown {label} fields: {', '.join(unknown)}")


def _threshold(value: Any, key: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ContractValidationError(f"{key} must be between 0 and 1")


__all__ = [
    "ContractLoader",
    "ContractValidationError",
    "DecisionContract",
    "FieldSpec",
    "SCHEMA_VERSION",
]
