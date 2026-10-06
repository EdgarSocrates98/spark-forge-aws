"""Provider-independent deterministic execution planning."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

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


def _mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    """Yield nested mapping evidence without interpreting free-form prose."""
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _mappings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _mappings(child)


def _flag(maps: Iterable[Mapping[str, Any]], *names: str) -> bool:
    wanted = set(names)
    for item in maps:
        for name in wanted:
            value = item.get(name)
            if value is True or (
                isinstance(value, str)
                and value.casefold() in {"true", "yes", "high"}
            ):
                return True
    return False


def derive_triggers(items: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Derive planner triggers from explicit evidence fields.

    Capability presence never counts as an answer. Only structured evidence is
    considered here; arbitrary snippets and descriptions remain untrusted data.
    """
    found: set[str] = set()
    for item in items:
        maps = tuple(_mappings(item))
        kind = str(item.get("kind", item.get("type", ""))).casefold()
        if _flag(maps, "conflicting_rules", "rule_conflict", "conflict"):
            found.add("conflicting_rules")
        if _flag(maps, "authority_conflict"):
            found.add("authority_conflict")
        if _flag(maps, "high_risk_change", "production_impact", "destructive"):
            found.add("high_risk_change")
        if _flag(maps, "confidence_gap", "low_confidence"):
            found.add("confidence_gap")
        if _flag(maps, "missing_evidence", "evidence_missing"):
            found.add("missing_evidence")
        if kind == "unresolved" or _flag(maps, "unresolved_reference"):
            found.add("unresolved_reference")

        for mapping in maps:
            risk = mapping.get("risk_level", mapping.get("risk"))
            if isinstance(risk, str) and risk.casefold() in {"high", "critical"}:
                found.add("high_risk_change")
            confidence = mapping.get("confidence")
            if isinstance(confidence, str) and confidence.casefold() in {
                "low",
                "very_low",
                "unknown",
            }:
                found.add("confidence_gap")
            elif isinstance(confidence, (int, float)) and confidence < 0.5:
                found.add("confidence_gap")
            code = str(mapping.get("code", "")).casefold()
            if "unresolved" in code:
                found.add("unresolved_reference")
            if "missing_evidence" in code or "evidence_missing" in code:
                found.add("missing_evidence")
    return normalize_triggers(found)


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


__all__ = [
    "ExecutionPlan",
    "PlanKind",
    "derive_triggers",
    "normalize_triggers",
    "plan_execution",
]
