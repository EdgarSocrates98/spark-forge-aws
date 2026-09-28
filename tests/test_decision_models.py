from __future__ import annotations

import pytest

from sparkforge.economy.decision_models import (
    BudgetSnapshot,
    DecisionInput,
    DecisionStatus,
    ProviderUsage,
)


def test_decision_input_canonicalizes_evidence_and_separates_bytes_from_tokens() -> None:
    request = DecisionInput.from_mapping(
        {
            "task_id": "task-1",
            "task_description": "diagnose Glue",
            "evidence_kinds": ["rule", "fact", "rule"],
            "evidence_ids": ["f2", "f1"],
            "payload_bytes": 128,
            "provider_usage": {
                "provider_tokens": {"input_tokens": 3, "output_tokens": 2},
                "transcript_sha256": "abc",
            },
        }
    )

    assert request.evidence_kinds == ("fact", "rule")
    assert request.evidence_ids == ("f1", "f2")
    assert request.canonical()["payload_bytes"] == 128
    assert request.provider_usage.to_dict()["provider_tokens"]["total_tokens"] == 5


def test_unresolved_provider_usage_never_estimates_from_payload_bytes() -> None:
    usage = ProviderUsage.unresolved("host_transcript_absent")

    assert usage.to_dict() == {
        "provider_tokens": None,
        "tokens_unresolved": True,
        "unresolved_reason": "host_transcript_absent",
    }


def test_models_reject_invalid_budget_and_empty_input() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        BudgetSnapshot(tokens_used=-1)
    with pytest.raises(ValueError, match="task_id"):
        DecisionInput("", "task")
    assert DecisionStatus.ACCEPTED.value == "accepted"
