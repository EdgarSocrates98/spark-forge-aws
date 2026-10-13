"""Closed deterministic primitive evaluators."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from sparkforge_aws.decision.conditions import condition_matches
from sparkforge_aws.decision.contracts import ContractValidationError, DecisionContract
from sparkforge_aws.decision.models import DecisionStatus, EvaluationOutcome, PrimitiveKind


class PrimitiveEvaluator(Protocol):
    kind: PrimitiveKind

    def evaluate(
        self, contract: DecisionContract, state: Mapping[str, Any]
    ) -> EvaluationOutcome: ...


class ChoiceEvaluator:
    kind = PrimitiveKind.CHOICE

    def evaluate(self, contract: DecisionContract, state: Mapping[str, Any]) -> EvaluationOutcome:
        spec = contract.spec
        field = str(spec.get("select_field", "choice"))
        value = state.get(field)
        if value is None:
            return _unresolved(f"missing_state.{field}", self.kind.value)
        selected = str(value)
        if selected not in {str(item) for item in spec["options"]}:
            return _abstain("choice_not_declared", self.kind.value, (field,))
        confidence = float(spec.get("confidence", 1.0))
        confidence_by_option = spec.get("confidence_by_option", {})
        if isinstance(confidence_by_option, Mapping) and selected in confidence_by_option:
            confidence = float(confidence_by_option[selected])
        threshold = float(spec.get("threshold", 0.0))
        if confidence < threshold:
            return _abstain("below_acceptance_threshold", self.kind.value, (field,))
        return _accepted(selected, self.kind.value, confidence, (field,))


class BooleanEvaluator:
    kind = PrimitiveKind.BOOLEAN

    def evaluate(self, contract: DecisionContract, state: Mapping[str, Any]) -> EvaluationOutcome:
        field = str(contract.spec["field"])
        if field not in state:
            return _unresolved(f"missing_state.{field}", self.kind.value)
        if not isinstance(state[field], bool):
            return _unresolved(f"invalid_state_type.{field}", self.kind.value)
        return _accepted(str(state[field]).lower(), self.kind.value, 1.0, (field,))


class GateEvaluator:
    kind = PrimitiveKind.GATE

    def evaluate(self, contract: DecisionContract, state: Mapping[str, Any]) -> EvaluationOutcome:
        for requirement in contract.spec["requirements"]:
            field = str(requirement["field"])
            if field not in state:
                return _unresolved(f"missing_state.{field}", self.kind.value)
            if not condition_matches(requirement, state):
                return _abstain("gate_closed", self.kind.value, (field,))
        return _accepted(str(contract.spec.get("on_pass", "open")), self.kind.value, 1.0)


class ScoreEvaluator:
    kind = PrimitiveKind.SCORE

    def evaluate(self, contract: DecisionContract, state: Mapping[str, Any]) -> EvaluationOutcome:
        score = 0.0
        evidence: list[str] = []
        for field, weight in contract.spec["weights"].items():
            if field not in state:
                return _unresolved(f"missing_state.{field}", self.kind.value)
            value = state[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return _unresolved(f"invalid_state_type.{field}", self.kind.value)
            score += float(value) * float(weight)
            evidence.append(str(field))
        threshold = float(contract.spec.get("threshold", 0.0))
        if score < threshold:
            return _abstain("below_acceptance_threshold", self.kind.value, tuple(evidence))
        return _accepted(
            str(contract.spec.get("on_pass", "score_pass")),
            self.kind.value,
            min(1.0, max(0.0, score)),
            tuple(evidence),
        )


class RouteEvaluator:
    kind = PrimitiveKind.ROUTE

    def evaluate(self, contract: DecisionContract, state: Mapping[str, Any]) -> EvaluationOutcome:
        for rule in sorted(contract.spec["rules"], key=lambda item: int(item.get("priority", 100))):
            conditions = rule.get("when", [])
            if all(condition_matches(condition, state) for condition in conditions):
                route = str(rule.get("route", rule.get("target")))
                confidence = float(rule.get("confidence", 1.0))
                threshold = float(rule.get("threshold", 0.0))
                if confidence < threshold:
                    return _abstain("below_acceptance_threshold", self.kind.value)
                return _accepted(route, self.kind.value, confidence)
        default = contract.spec.get("default")
        if default is not None:
            if str(default).casefold() == "abstain":
                return _abstain("no_route_matched", self.kind.value)
            return _accepted(
                str(default), self.kind.value, float(contract.spec.get("default_confidence", 1.0))
            )
        return _abstain("no_route_matched", self.kind.value)


class ThresholdEvaluator:
    kind = PrimitiveKind.THRESHOLD

    def evaluate(self, contract: DecisionContract, state: Mapping[str, Any]) -> EvaluationOutcome:
        spec = contract.spec
        field = str(spec["field"])
        if field not in state:
            return _unresolved(f"missing_state.{field}", self.kind.value)
        actual = state[field]
        expected = spec["value"]
        try:
            passed = _compare(actual, expected, str(spec["operator"]))
        except TypeError:
            return _unresolved(f"invalid_state_type.{field}", self.kind.value)
        if passed:
            selected = str(spec["on_pass"])
            return _accepted(
                selected, self.kind.value, float(spec.get("confidence", 1.0)), (field,)
            )
        return _abstain(str(spec.get("on_fail", "below_threshold")), self.kind.value, (field,))


PRIMITIVES: dict[PrimitiveKind, PrimitiveEvaluator] = {
    PrimitiveKind.CHOICE: ChoiceEvaluator(),
    PrimitiveKind.BOOLEAN: BooleanEvaluator(),
    PrimitiveKind.GATE: GateEvaluator(),
    PrimitiveKind.SCORE: ScoreEvaluator(),
    PrimitiveKind.ROUTE: RouteEvaluator(),
    PrimitiveKind.THRESHOLD: ThresholdEvaluator(),
}


def evaluator_for(kind: PrimitiveKind) -> PrimitiveEvaluator:
    try:
        return PRIMITIVES[kind]
    except KeyError as exc:
        raise ContractValidationError(f"unknown primitive: {kind.value}") from exc


def _compare(actual: Any, expected: Any, operator: str) -> bool:
    if operator == "gt":
        return actual > expected
    if operator == "gte":
        return actual >= expected
    if operator == "lt":
        return actual < expected
    if operator == "lte":
        return actual <= expected
    return actual == expected


def _accepted(
    value: str, method: str, confidence: float, evidence: tuple[str, ...] = ()
) -> EvaluationOutcome:
    return EvaluationOutcome(DecisionStatus.ACCEPTED, (value,), method, confidence, None, evidence)


def _abstain(reason: str, method: str, evidence: tuple[str, ...] = ()) -> EvaluationOutcome:
    return EvaluationOutcome(DecisionStatus.ABSTAIN, (), method, None, reason, evidence)


def _unresolved(reason: str, method: str) -> EvaluationOutcome:
    return EvaluationOutcome(DecisionStatus.UNRESOLVED, (), method, None, reason, ())


__all__ = ["PRIMITIVES", "PrimitiveEvaluator", "evaluator_for"]
