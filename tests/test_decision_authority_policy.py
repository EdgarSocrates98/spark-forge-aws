from __future__ import annotations

from sparkforge.decision import AuthorityPolicy, PromotionEvidence


def _raw(*, active_enabled: bool = False) -> dict:
    return {
        "schema_version": 1,
        "policy_version": "policy-test-v1",
        "authority": {
            "default_mode": "shadow",
            "active": {
                "enabled": active_enabled,
                "minimum_labeled_tasks": 2,
                "require_quality_gate": True,
                "require_economy_gate": True,
                "require_ci_gate": True,
                "require_rollback": True,
            },
        },
    }


class _Contract:
    contract_id = "contract"
    contract_version = "1"
    sha256 = "contract-sha"
    activation_enabled = True


def _evidence() -> PromotionEvidence:
    return PromotionEvidence(
        promotion_id="promotion",
        contract_id="contract",
        contract_version="1",
        contract_sha256="contract-sha",
        labeled_tasks=2,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        rollback="restore-shadow",
        evidence_refs=("benchmark:holdout",),
    )


def test_shadow_is_observation_only_and_carries_policy_identity() -> None:
    decision = AuthorityPolicy(_raw()).authorize_promotion(mode="shadow", contract=_Contract())
    assert decision.allowed is True
    assert decision.policy_version == "policy-test-v1"


def test_assisted_requires_explicit_caller_authority() -> None:
    decision = AuthorityPolicy(_raw()).authorize_promotion(
        mode="assisted", contract=_Contract()
    )
    assert decision.allowed is False
    assert decision.reason == "explicit_authority_required"


def test_active_disabled_wins_before_promotion_evidence() -> None:
    decision = AuthorityPolicy(_raw()).authorize_promotion(
        mode="active",
        contract=_Contract(),
        evidence=_evidence(),
        caller_authorized=True,
    )
    assert decision.allowed is False
    assert decision.reason == "active_disabled_by_policy"


def test_active_requires_complete_evidence_when_explicitly_enabled() -> None:
    decision = AuthorityPolicy(_raw(active_enabled=True)).authorize_promotion(
        mode="active",
        contract=_Contract(),
        evidence=_evidence(),
        caller_authorized=True,
    )
    assert decision.allowed is True
    assert decision.evidence_refs == ("benchmark:holdout",)
