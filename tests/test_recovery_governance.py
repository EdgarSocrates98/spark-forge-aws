from __future__ import annotations

from sparkforge.agentic.budget import CaseBudget
from sparkforge.agentic.control import RecoveryGovernor
from sparkforge.agentic.recovery import FailureClass


def test_recovery_consumes_case_budget_and_records_governor():
    budget = CaseBudget(max_retries=1, max_replans=1)
    result = RecoveryGovernor().resolve(
        FailureClass.TRANSIENT_HOST,
        attempt=0,
        strategy_fingerprint="strategy-a",
        profile="economy",
        risk="low",
        budget=budget,
    )
    assert result.decision.action == "retry"
    assert result.budget_consumed is True
    assert budget.retries_used == 1
    assert result.governor.limits.max_retries == 1


def test_recovery_stops_when_case_budget_is_exhausted():
    budget = CaseBudget(max_retries=0)
    result = RecoveryGovernor().resolve(
        FailureClass.TRANSIENT_HOST,
        attempt=0,
        strategy_fingerprint="strategy-a",
        profile="economy",
        risk="low",
        budget=budget,
    )
    assert result.decision.action == "stop"
    assert result.decision.terminal is True
    assert result.decision.reason in {
        "governor_recovery_budget_exhausted",
        "case_budget_recovery_exhausted",
    }


def test_repeated_replan_is_terminal():
    result = RecoveryGovernor().resolve(
        FailureClass.STRATEGY_REJECTED,
        attempt=0,
        strategy_fingerprint="strategy-a",
        history=("strategy-a",),
    )
    assert result.decision.action == "stop"
    assert result.decision.terminal is True
