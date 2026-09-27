"""Provider-independent deterministic execution planning."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

PlanKind = Literal["deterministic", "specialist", "reviewer", "debate", "unresolved"]
AnswerStatus = Literal["resolved", "partial", "unavailable"]

_TRIGGER_ALIASES = {
    "conflict": "conflicting_rules",
    "conflicting rule": "conflicting_rules",
    "authority conflict": "authority_conflict",
    "high risk": "high_risk_change",
    "confidence gap": "confidence_gap",
    "missing evidence": "missing_evidence",
    "unresolved reference": "unresolved_reference",
}


def normalize_triggers(triggers: Iterable[str]) -> tuple[str, ...]:
    normalized: set[str] = set()
    for trigger in triggers:
        value = "_".join(str(trigger).casefold().strip().replace("-", " ").split())
        normalized.add(_TRIGGER_ALIASES.get(value, value))
    return tuple(sorted(item for item in normalized if item))


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
    answer_status: AnswerStatus | None = None,
) -> ExecutionPlan:
    """Choose the smallest valid plan; never invokes a provider."""
    if answer_status is not None and answer_status not in {
        "resolved",
        "partial",
        "unavailable",
    }:
        raise ValueError(f"invalid answer status: {answer_status}")
    resolved = (
        answer_status == "resolved"
        if answer_status is not None
        else has_deterministic_answer
    )
    active = normalize_triggers(triggers)
    if resolved and not active:
        return ExecutionPlan("deterministic", "deterministic_first", complexity="low")
    if not allow_agentic_escalation:
        if resolved:
            return ExecutionPlan("deterministic", "escalation_disabled", active, "low")
        reason = "agentic_escalation_disabled"
        if answer_status == "partial":
            reason = "partial_answer_escalation_disabled"
        elif answer_status == "unavailable":
            reason = "answer_unavailable"
        return ExecutionPlan("unresolved", reason, active)
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
    reason = "no_deterministic_basis" if answer_status != "unavailable" else "answer_unavailable"
    return ExecutionPlan("unresolved", reason, active)


__all__ = ["ExecutionPlan", "PlanKind", "normalize_triggers", "plan_execution"]
