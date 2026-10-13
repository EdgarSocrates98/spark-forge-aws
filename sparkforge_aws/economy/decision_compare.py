"""Comparison of authoritative router output and shadow Decision Plane output."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sparkforge_aws.economy.decision_models import (
    ComparisonState,
    DecisionComparison,
    DecisionResult,
)


def compare_decisions(
    current: Any,
    shadow: DecisionResult,
) -> DecisionComparison:
    """Classify exactly one comparison state without changing either result."""
    current_route = _route_from_current(current)
    shadow_route = shadow.selected[0] if shadow.selected else None
    if current_route and shadow_route:
        state = (
            ComparisonState.AGREEMENT
            if current_route == shadow_route
            else ComparisonState.DISAGREEMENT
        )
        return DecisionComparison(state, current_route, shadow_route)
    if current_route or shadow_route:
        reason = "shadow_unresolved" if shadow_route is None else "current_route_unresolved"
        return DecisionComparison(
            ComparisonState.COVERAGE_GAP,
            current_route,
            shadow_route,
            (reason,),
        )
    reasons = shadow.unresolved or ("both_decisions_unresolved",)
    return DecisionComparison(
        ComparisonState.UNRESOLVED,
        current_route,
        shadow_route,
        tuple(reasons),
    )


def _route_from_current(current: Any) -> str | None:
    if current is None:
        return None
    if isinstance(current, str):
        return current.strip() or None
    if isinstance(current, Mapping):
        value = current.get("route") or current.get("selected") or current.get("current_route")
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        return str(value).strip() if value else None
    route = getattr(current, "tier", None)
    if route is not None:
        value = getattr(route, "value", route)
        return str(value).strip() or None
    return None


def comparison_is_resolved(comparison: DecisionComparison) -> bool:
    return comparison.state in {
        ComparisonState.AGREEMENT,
        ComparisonState.DISAGREEMENT,
    }


__all__ = ["compare_decisions", "comparison_is_resolved"]
