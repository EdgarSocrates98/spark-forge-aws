"""Pure deterministic evaluation of versioned Decision Plane contracts."""

from __future__ import annotations

from collections.abc import Iterable

from sparkforge.economy.decision_contracts import Candidate, DecisionContract, Predicate
from sparkforge.economy.decision_models import DecisionInput, DecisionResult, DecisionStatus


class DeterministicDecisionEngine:
    """Evaluate declared predicates without dispatching work."""

    def evaluate(self, contract: DecisionContract, state: DecisionInput) -> DecisionResult:
        if contract.mode != "shadow":
            return DecisionResult.refused_result(
                contract, state.budget, "decision_contract_not_shadow"
            )
        budget_reason = self._budget_reason(contract, state)
        if budget_reason is not None:
            return DecisionResult.unresolved_result(contract, state.budget, budget_reason)
        for candidate in sorted(contract.candidates, key=lambda item: item.priority):
            if all(self._matches(predicate, state) for predicate in candidate.predicates):
                return DecisionResult(
                    contract_id=contract.contract_id,
                    contract_version=contract.contract_version,
                    contract_sha256=contract.sha256,
                    status=DecisionStatus.ACCEPTED,
                    selected=(candidate.route,),
                    confidence=contract.thresholds.confidence_for(candidate.name),
                    confidence_source="rule",
                    method="declared_predicates",
                    budget=state.budget,
                )
        return DecisionResult.unresolved_result(
            contract, state.budget, "no_candidate_has_sufficient_evidence"
        )

    @staticmethod
    def _budget_reason(contract: DecisionContract, state: DecisionInput) -> str | None:
        if (
            state.budget.max_total_tokens is not None
            and state.budget.tokens_used > contract.budget.max_total_tokens
        ):
            return "budget_tokens_exceeded"
        if (
            state.budget.max_tool_calls is not None
            and state.budget.tool_calls_used > contract.budget.max_tool_calls
        ):
            return "budget_tool_calls_exceeded"
        return None

    @staticmethod
    def _matches(predicate: Predicate, state: DecisionInput) -> bool:
        value = predicate.value
        if predicate.name == "always":
            return True
        if predicate.name == "deterministic_available":
            return state.deterministic_available is bool(value)
        if predicate.name == "cached":
            return state.cached is bool(value)
        if predicate.name == "evidence_kind":
            return str(value) in state.evidence_kinds
        if predicate.name == "profile_is":
            return state.profile == str(value)
        if predicate.name == "risk_is":
            return state.risk_level == str(value)
        if predicate.name == "task_contains":
            return str(value).casefold() in state.task_description.casefold()
        return False


def candidate_routes(candidates: Iterable[Candidate]) -> tuple[str, ...]:
    """Return declared routes in stable contract order for diagnostics."""
    return tuple(
        candidate.route for candidate in sorted(candidates, key=lambda item: item.priority)
    )


__all__ = ["DeterministicDecisionEngine", "candidate_routes"]
