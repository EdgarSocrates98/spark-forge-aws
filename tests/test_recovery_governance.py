from __future__ import annotations

from sparkforge_aws.agentic.budget import CaseBudget
from sparkforge_aws.agentic.control import RecoveryGovernor
from sparkforge_aws.agentic.recovery import FailureClass


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


def test_replan_budget_is_independent_from_zero_retry_budget():
    budget = CaseBudget(max_retries=0, max_replans=1)
    result = RecoveryGovernor().resolve(
        FailureClass.STRATEGY_REJECTED,
        attempt=0,
        strategy_fingerprint="strategy-replan",
        profile="economy",
        risk="low",
        budget=budget,
    )
    assert result.decision.action == "replan"
    assert result.budget_consumed is True
    assert budget.replans_used == 1
    assert budget.retries_used == 0
    assert result.budget_before["replans_used"] == 0
    assert result.budget_after["replans_used"] == 1


def test_zero_recovery_quota_does_not_exhaust_main_case_budget():
    budget = CaseBudget(max_retries=0, max_replans=1)
    assert budget.status.value == "within"
    budget.consume_agent()
    assert budget.agents_spawned == 1
    try:
        budget.consume_retry()
    except Exception as exc:
        assert str(exc) == "retry_budget_exhausted"
    else:
        raise AssertionError("retry must remain independently refused")


def test_repeated_cycle_is_rejected_before_second_budget_charge():
    budget = CaseBudget(max_retries=2, max_replans=2)
    governor = RecoveryGovernor()
    first = governor.resolve(
        FailureClass.STRATEGY_REJECTED,
        attempt=0,
        strategy_fingerprint="same-cycle",
        budget=budget,
    )
    second = governor.resolve(
        FailureClass.STRATEGY_REJECTED,
        attempt=1,
        strategy_fingerprint="same-cycle",
        budget=budget,
    )
    assert first.budget_consumed is True
    assert second.decision.action == "stop"
    assert second.decision.reason == "strategy_fingerprint_repeated"
    assert budget.replans_used == 1
