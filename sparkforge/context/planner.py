"""Provider-independent deterministic execution planning."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

PlanKind = Literal["deterministic", "specialist", "reviewer", "debate", "unresolved"]


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    kind: PlanKind
    reason: str
    triggers: tuple[str, ...] = ()
    complexity: Literal["low", "medium", "high", "unknown"] = "unknown"
    reasoning_required: bool = False
    parallelism_useful: bool = False
    provider_hint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "reason": self.reason,
            "triggers": list(self.triggers),
            "complexity": self.complexity,
            "reasoning_required": self.reasoning_required,
            "parallelism_useful": self.parallelism_useful,
            "provider_hint": self.provider_hint,
        }


def plan_execution(
    *,
    has_deterministic_answer: bool,
    triggers: Iterable[str] = (),
    allow_agentic_escalation: bool = False,
) -> ExecutionPlan:
    """Choose the smallest valid plan; never invokes a provider."""
    active = tuple(sorted(set(str(trigger) for trigger in triggers if str(trigger))))
    if has_deterministic_answer and not active:
        return ExecutionPlan("deterministic", "deterministic_first", complexity="low")
    if not allow_agentic_escalation:
        if has_deterministic_answer:
            return ExecutionPlan("deterministic", "escalation_disabled", active, "low")
        return ExecutionPlan("unresolved", "agentic_escalation_disabled", active)
    if {"conflicting_rules", "authority_conflict"} & set(active):
        return ExecutionPlan(
            "debate",
            "escalation_triggered",
            active,
            "high",
            reasoning_required=True,
            parallelism_useful=True,
        )
    if {"high_risk_change", "confidence_gap"} & set(active):
        return ExecutionPlan(
            "reviewer",
            "review_triggered",
            active,
            "high",
            reasoning_required=True,
        )
    if active:
        return ExecutionPlan(
            "specialist",
            "specialist_triggered",
            active,
            "medium",
            reasoning_required=True,
        )
    return ExecutionPlan("unresolved", "no_deterministic_basis")


__all__ = ["ExecutionPlan", "PlanKind", "plan_execution"]
