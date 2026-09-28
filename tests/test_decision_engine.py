from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from sparkforge.economy.decision_contracts import ContractRegistry
from sparkforge.economy.decision_engine import DeterministicDecisionEngine, candidate_routes
from sparkforge.economy.decision_models import DecisionInput, DecisionStatus

ROOT = Path(__file__).resolve().parents[1]


def test_engine_selects_first_matching_declared_candidate() -> None:
    contract = ContractRegistry(ROOT).load("routing.data_domain")
    state = DecisionInput("task", "diagnose", deterministic_available=True)

    result = DeterministicDecisionEngine().evaluate(contract, state)

    assert result.status is DecisionStatus.ACCEPTED
    assert result.selected == ("tier_0_deterministic",)
    assert candidate_routes(contract.candidates)[0] == "tier_0_deterministic"


def test_insufficient_evidence_is_unresolved() -> None:
    contract = ContractRegistry(ROOT).load("routing.data_domain")
    without_default = replace(
        contract,
        candidates=tuple(
            candidate for candidate in contract.candidates if candidate.name != "default"
        ),
    )
    state = DecisionInput("task", "no matching evidence")

    result = DeterministicDecisionEngine().evaluate(without_default, state)

    assert result.status is DecisionStatus.UNRESOLVED
    assert result.selected == ()
    assert result.confidence is None


def test_budget_excess_is_unresolved() -> None:
    contract = ContractRegistry(ROOT).load("routing.data_domain")
    state = DecisionInput("task", "diagnose", budget=replace(contract.budget, tokens_used=8001))

    result = DeterministicDecisionEngine().evaluate(contract, state)

    assert result.status is DecisionStatus.UNRESOLVED
    assert result.unresolved == ("budget_tokens_exceeded",)
