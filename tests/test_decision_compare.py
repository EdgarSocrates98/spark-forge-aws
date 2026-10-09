from __future__ import annotations

from pathlib import Path

from sparkforge_aws.economy.decision_compare import compare_decisions, comparison_is_resolved
from sparkforge_aws.economy.decision_contracts import ContractRegistry
from sparkforge_aws.economy.decision_engine import DeterministicDecisionEngine
from sparkforge_aws.economy.decision_models import (
    ComparisonState,
    DecisionInput,
    DecisionResult,
)

ROOT = Path(__file__).resolve().parents[1]


def _shadow(route: str | None = None):
    contract = ContractRegistry(ROOT).load("routing.data_domain")
    state = DecisionInput("task", "diagnose", current_route=route)
    return DeterministicDecisionEngine().evaluate(contract, state)


def test_same_selection_is_agreement() -> None:
    comparison = compare_decisions("tier_3_cheap_local", _shadow())

    assert comparison.state is ComparisonState.AGREEMENT
    assert comparison_is_resolved(comparison)


def test_different_selection_is_disagreement() -> None:
    comparison = compare_decisions("tier_5_premium", _shadow())

    assert comparison.state is ComparisonState.DISAGREEMENT


def test_one_side_missing_is_coverage_gap() -> None:
    comparison = compare_decisions(None, _shadow())

    assert comparison.state is ComparisonState.COVERAGE_GAP


def test_both_sides_missing_is_unresolved() -> None:
    contract = ContractRegistry(ROOT).load("routing.data_domain")
    no_match = DecisionResult.unresolved_result(contract, DecisionInput("x", "x").budget, "missing")
    comparison = compare_decisions(None, no_match)

    assert comparison.state is ComparisonState.UNRESOLVED
