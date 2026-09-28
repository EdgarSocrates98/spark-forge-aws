from __future__ import annotations

from sparkforge.economy.decision_activation import ActivationEvidence, guard_activation


def test_shadow_mode_is_always_allowed() -> None:
    decision = guard_activation("shadow", ActivationEvidence(0, False, False))

    assert decision.allowed is True
    assert decision.unresolved == ()


def test_activation_refuses_small_or_incomplete_corpus() -> None:
    decision = guard_activation("active", ActivationEvidence(49, True, False))

    assert decision.allowed is False
    assert decision.unresolved == (
        "activation_corpus_below_50_labeled_tasks",
        "activation_economy_gate_missing",
    )


def test_unknown_mode_is_refused() -> None:
    decision = guard_activation("production", ActivationEvidence(100, True, True))

    assert decision.allowed is False
    assert decision.unresolved == ("unsupported_activation_mode",)


def test_active_mode_is_allowed_only_with_complete_evidence() -> None:
    decision = guard_activation("active", ActivationEvidence(50, True, True))

    assert decision.allowed is True
    assert decision.unresolved == ()
