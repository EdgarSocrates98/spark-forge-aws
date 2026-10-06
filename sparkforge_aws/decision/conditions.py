"""Shared structural validation and matching for bounded conditions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CONDITION_FIELDS = frozenset({"field", "equals", "in", "contains", "truthy"})


class ConditionValidationError(ValueError):
    """Invalid condition shape at contract load time."""


def validate_condition(raw: Any, *, label: str = "condition") -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ConditionValidationError(f"{label} must be a mapping")
    unknown = sorted(set(raw) - CONDITION_FIELDS)
    if unknown:
        raise ConditionValidationError(f"unknown {label} fields: {', '.join(unknown)}")
    field = raw.get("field")
    if not isinstance(field, str) or not field.strip():
        raise ConditionValidationError(f"{label}.field is required")
    operators = [name for name in ("equals", "in", "contains", "truthy") if name in raw]
    if len(operators) != 1:
        raise ConditionValidationError(
            f"{label} must declare exactly one operator: equals, in, contains or truthy"
        )
    operator = operators[0]
    value = raw[operator]
    if operator == "in":
        if not isinstance(value, list) or not value:
            raise ConditionValidationError(f"{label}.in must be a non-empty list")
    elif operator == "truthy" and not isinstance(value, bool):
        raise ConditionValidationError(f"{label}.truthy must be boolean")
    return {str(key): value for key, value in raw.items()}


def validate_conditions(raw: Any, *, label: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list):
        raise ConditionValidationError(f"{label} must be a list")
    return tuple(
        validate_condition(condition, label=f"{label}[{index}]")
        for index, condition in enumerate(raw)
    )


def condition_matches(condition: Mapping[str, Any], state: Mapping[str, Any]) -> bool:
    field = condition["field"]
    if field not in state:
        return False
    value = state[field]
    if "equals" in condition:
        return value == condition["equals"]
    if "in" in condition:
        return value in condition["in"]
    if "contains" in condition:
        candidate = condition["contains"]
        return isinstance(value, (list, tuple, str)) and candidate in value
    return bool(value) is bool(condition["truthy"])


__all__ = [
    "CONDITION_FIELDS",
    "ConditionValidationError",
    "condition_matches",
    "validate_condition",
    "validate_conditions",
]
