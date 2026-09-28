from __future__ import annotations

import pytest

from sparkforge.agentic.recovery import FailureClass, RecoveryPolicy


def test_recovery_covers_all_eight_failure_classes_with_one_action() -> None:
    policy = RecoveryPolicy()
    decisions = {
        failure: policy.next(failure, attempt=0, strategy_fingerprint=f"strategy-{failure.value}")
        for failure in FailureClass
    }
    assert len(decisions) == 8
    assert all(item.action for item in decisions.values())
    assert decisions[FailureClass.INVALID_INPUT].action == "refuse"
    assert decisions[FailureClass.MISSING_EVIDENCE].action == "abstain"


@pytest.mark.parametrize("failure", [FailureClass.TRANSIENT_HOST, FailureClass.TIMEOUT])
def test_retry_stops_at_configured_limit(failure: FailureClass) -> None:
    decision = RecoveryPolicy(max_attempts=2).next(
        failure,
        attempt=2,
        strategy_fingerprint="same",
    )
    assert decision.action == "stop"
    assert decision.terminal is True
    assert decision.reason == "retry_limit_exceeded"


def test_repeated_strategy_never_retries_unchanged() -> None:
    decision = RecoveryPolicy().next(
        FailureClass.TRANSIENT_HOST,
        attempt=0,
        strategy_fingerprint="same",
        history=("same",),
    )
    assert decision.action == "replan"
    assert decision.reason == "strategy_fingerprint_repeated"
