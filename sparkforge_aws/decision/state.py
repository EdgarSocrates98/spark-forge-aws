"""Declared state compilation for bounded decisions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from sparkforge_aws.decision.contracts import DecisionContract, FieldSpec
from sparkforge_aws.decision.models import CompiledState


class StateCompilationError(ValueError):
    """Invalid state shape at the kernel boundary."""


class StateCompiler:
    """Compile only declared, JSON-compatible state without inference."""

    def compile(self, contract: DecisionContract, raw_state: Mapping[str, Any]) -> CompiledState:
        if not isinstance(raw_state, Mapping):
            raise StateCompilationError("state must be a mapping")
        unresolved: list[str] = []
        field_by_name = {field.name: field for field in contract.state_fields}
        values: dict[str, Any] = {}
        required_fields = set(contract.required_state_fields)
        for field in contract.state_fields:
            if field.name not in raw_state or raw_state[field.name] is None:
                if field.name in required_fields:
                    unresolved.append(f"missing_state.{field.name}")
                continue
            value = raw_state[field.name]
            if not _matches_type(value, field.value_type):
                unresolved.append(f"invalid_state_type.{field.name}")
                continue
            values[field.name] = _normalize(value, field)
        for key, value in raw_state.items():
            name = str(key)
            if name in values or name in field_by_name:
                continue
            if not contract.additional_properties:
                unresolved.append(f"undeclared_state.{name}")
                continue
            values[name] = _normalize(value, FieldSpec(name))
        ordered = tuple(sorted(values.items(), key=lambda item: item[0]))
        state_bytes = len(_canonical(ordered).encode("utf-8"))
        if state_bytes > contract.max_input_bytes:
            unresolved.append("input_payload_exceeds_budget")
        return CompiledState(ordered, tuple(dict.fromkeys(unresolved)))


def _matches_type(value: Any, value_type: str) -> bool:
    if value_type == "any":
        return _json_compatible(value)
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "array":
        return isinstance(value, list)
    if value_type == "object":
        return isinstance(value, Mapping)
    return False


def _json_compatible(value: Any) -> bool:
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _normalize(value: Any, field: FieldSpec) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item, FieldSpec(str(key)))
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        normalized = [_normalize(item, FieldSpec(field.name)) for item in value]
        if field.order_insensitive:
            return sorted(
                normalized,
                key=lambda item: json.dumps(
                    item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
            )
        return normalized
    return value


def _canonical(values: tuple[tuple[str, Any], ...]) -> str:
    return json.dumps(dict(values), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


__all__ = ["StateCompilationError", "StateCompiler"]
