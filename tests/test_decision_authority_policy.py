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
                "require_contract_sha256": True,
                "require_calibration_match": True,
                "require_evidence_refs": True,
            },
        },
    }


class _Contract:
    contract_id = "contract"
    contract_version = "1"
    sha256 = "contract-sha"
    activation_enabled = True
    calibration_version = "none"


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


def test_authority_rejects_truthy_string_booleans() -> None:
    raw = _raw()
    raw["authority"]["active"]["enabled"] = "false"
    try:
        AuthorityPolicy(raw)
    except ValueError as exc:
        assert "must be boolean" in str(exc)
    else:
        raise AssertionError("string boolean must fail closed")


def test_active_requires_contract_calibration_and_evidence_identity() -> None:
    raw = _raw(active_enabled=True)
    raw["authority"]["active"].update(
        {
            "require_contract_sha256": True,
            "require_calibration_match": True,
            "require_evidence_refs": True,
        }
    )
    contract = _Contract()
    contract.calibration_version = "calibration-v2"
    evidence = _evidence()
    evidence = PromotionEvidence(
        promotion_id=evidence.promotion_id,
        contract_id=evidence.contract_id,
        contract_version=evidence.contract_version,
        labeled_tasks=evidence.labeled_tasks,
        quality_gate=evidence.quality_gate,
        economy_gate=evidence.economy_gate,
        ci_verified=evidence.ci_verified,
        rollback=evidence.rollback,
        calibration_version="calibration-v1",
    )
    decision = AuthorityPolicy(raw).authorize_promotion(
        mode="active", contract=contract, evidence=evidence, caller_authorized=True
    )
    assert decision.allowed is False
    assert "promotion_contract_sha256_missing" in decision.unresolved
    assert "promotion_calibration_version_mismatch" in decision.unresolved
    assert "promotion_evidence_refs_missing" in decision.unresolved


def test_authority_rejects_numeric_coercion_and_string_refs() -> None:
    raw = _raw()
    raw["authority"]["active"]["minimum_labeled_tasks"] = "2"
    try:
        AuthorityPolicy(raw)
    except ValueError as exc:
        assert "must be integer" in str(exc)
    else:
        raise AssertionError("string integer must fail closed")

    try:
        PromotionEvidence(evidence_refs="benchmark:holdout")
    except ValueError as exc:
        assert "sequence of strings" in str(exc)
    else:
        raise AssertionError("string refs must fail closed")
