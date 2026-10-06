"""FASE 11 — information gain / stop policy.

§85-88: antes de agente/review/debate/retrieval/escalação, avalia ganho
esperado sobre estado observado — política determinística, nunca pseudo-ML.
§90: taxonomia de falhas cobre as classes operacionais reais.
§92: retry não é default — recusa de segurança nunca tenta de novo.
"""

from __future__ import annotations

import pytest

from sparkforge.agentic.recovery import FailureClass, RecoveryPolicy
from sparkforge.agentic.stop import (
    ExpectedGainState,
    StopAction,
    StopDecision,
    StopPolicy,
)


class TestFailureTaxonomy:
    def test_covers_all_spec_classes(self) -> None:
        names = {item.value for item in FailureClass}
        for expected in (
            "provider_unavailable",
            "tool_failure",
            "invalid_input",
            "missing_evidence",
            "budget_exceeded",
            "timeout",
            "policy_conflict",
            "security_refusal",
            "context_insufficient",
            "loop",
            "dependency_failure",
        ):
            assert expected in names, expected

    def test_security_refusal_never_retries(self) -> None:
        policy = RecoveryPolicy(max_attempts=9)
        for attempt in (0, 1, 5):
            decision = policy.next(
                FailureClass.SECURITY_REFUSAL,
                attempt=attempt,
                strategy_fingerprint=f"s-{attempt}",
            )
            assert decision.action == "refuse"
            assert decision.terminal is True

    def test_loop_stops_immediately(self) -> None:
        decision = RecoveryPolicy().next(
            FailureClass.LOOP, attempt=0, strategy_fingerprint="x"
        )
        assert decision.action == "stop"
        assert decision.terminal is True

    def test_context_insufficient_replans_not_retries(self) -> None:
        decision = RecoveryPolicy().next(
            FailureClass.CONTEXT_INSUFFICIENT, attempt=0, strategy_fingerprint="c"
        )
        assert decision.action == "replan"

    def test_provider_unavailable_bounded_retry(self) -> None:
        policy = RecoveryPolicy(max_attempts=2)
        first = policy.next(
            FailureClass.PROVIDER_UNAVAILABLE, attempt=0, strategy_fingerprint="p0"
        )
        assert first.action == "retry"
        exhausted = policy.next(
            FailureClass.PROVIDER_UNAVAILABLE, attempt=2, strategy_fingerprint="p1"
        )
        assert exhausted.action == "stop"
        assert exhausted.reason == "retry_limit_exceeded"


class TestStopPolicy:
    def test_vocabulary(self) -> None:
        assert {a.value for a in StopAction} == {
            "stop_sufficient",
            "stop_budget",
            "stop_no_gain",
            "stop_security",
            "stop_unresolved",
            "continue",
            "review",
            "debate",
            "human",
        }

    def test_security_flag_wins_over_everything(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(
                pending_action="agent",
                security_flag=True,
                evidence_gaps=5,
                remaining_budget=1000,
            )
        )
        assert decision.action == StopAction.STOP_SECURITY

    def test_unresolved_required_state_stops(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(pending_action="review", unresolved_required=True)
        )
        assert decision.action == StopAction.STOP_UNRESOLVED

    def test_zero_budget_stops(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(
                pending_action="agent", evidence_gaps=3, remaining_budget=0
            )
        )
        assert decision.action == StopAction.STOP_BUDGET

    def test_no_gaps_no_novel_potential_is_sufficient(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(
                pending_action="context_expansion",
                evidence_gaps=0,
                novel_evidence_potential=False,
            )
        )
        assert decision.action == StopAction.STOP_SUFFICIENT

    def test_debate_without_contradiction_is_no_gain(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(
                pending_action="debate",
                task_risk="low",
                contradictions=0,
                agent_disagreement=False,
            )
        )
        assert decision.action == StopAction.STOP_NO_GAIN

    def test_debate_with_contradiction_continues(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(
                pending_action="debate",
                contradictions=2,
                evidence_gaps=1,
                novel_evidence_potential=True,
            )
        )
        assert decision.action == StopAction.DEBATE

    def test_high_risk_with_gaps_and_thin_budget_goes_human(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(
                pending_action="agent",
                task_risk="high",
                evidence_gaps=4,
                remaining_budget=10,
                novel_evidence_potential=True,
            )
        )
        assert decision.action == StopAction.HUMAN

    def test_gaps_with_room_continue(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(
                pending_action="retrieval",
                evidence_gaps=2,
                novel_evidence_potential=True,
                remaining_budget=5000,
                task_risk="low",
            )
        )
        assert decision.action == StopAction.CONTINUE

    def test_decision_serializes(self) -> None:
        decision = StopPolicy().evaluate(
            ExpectedGainState(pending_action="agent", security_flag=True)
        )
        raw = decision.to_dict()
        assert isinstance(decision, StopDecision)
        assert raw["action"] == "stop_security"
        assert raw["reason"]
        assert raw["pending_action"] == "agent"

    def test_unknown_pending_action_refused(self) -> None:
        with pytest.raises(ValueError, match="pending_action"):
            StopPolicy().evaluate(ExpectedGainState(pending_action="magic"))


class TestStopGovernedIntegration:
    """O gate de ganho mora no circuito governado, não num módulo solto."""

    def test_recovery_governor_accepts_gain_state(self) -> None:
        from sparkforge.agentic.control import RecoveryGovernor

        governor = RecoveryGovernor()
        governed = governor.resolve(
            FailureClass.TRANSIENT_HOST,
            attempt=0,
            strategy_fingerprint="fp-1",
            gain_state=ExpectedGainState(pending_action="agent", security_flag=True),
        )
        assert governed.decision.action == "stop"
        assert governed.decision.reason.startswith("stop_gate:")
        assert governed.decision.terminal is True

    def test_continue_leaves_recovery_untouched(self) -> None:
        from sparkforge.agentic.control import RecoveryGovernor

        governor = RecoveryGovernor()
        governed = governor.resolve(
            FailureClass.TRANSIENT_HOST,
            attempt=0,
            strategy_fingerprint="fp-2",
            gain_state=ExpectedGainState(
                pending_action="agent",
                evidence_gaps=2,
                novel_evidence_potential=True,
                remaining_budget=5000,
            ),
        )
        assert governed.decision.action == "retry"
