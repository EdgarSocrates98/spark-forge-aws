from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.decision import (
    ActivePromotion,
    AuthorityPolicy,
    BoundedDecisionKernel,
    ContractLoader,
    DecisionCache,
    DecisionStatus,
)
from sparkforge.economy.decision_contracts import ContractRegistry
from sparkforge.economy.decision_kernel_bridge import build_kernel_contract, evaluate_active
from sparkforge.economy.decision_models import DecisionInput

ROOT = Path(__file__).resolve().parents[1]


def _active_kernel_contract():
    raw = yaml.safe_load(
        (ROOT / "config/decisions/kernel.synthetic.yaml").read_text(encoding="utf-8")
    )
    raw["mode"] = "active"
    raw["activation"] = {"enabled": True}
    return ContractLoader(ROOT).parse(raw)


def _promotion(contract, **overrides):
    values = {
        "promotion_id": "promote-kernel-synthetic-v1",
        "contract_id": contract.contract_id,
        "contract_version": contract.contract_version,
        "contract_sha256": contract.sha256,
        "labeled_tasks": 50,
        "quality_gate": True,
        "economy_gate": True,
        "ci_verified": True,
        "rollback": "restore-shadow-and-legacy-router",
    }
    values.update(overrides)
    return ActivePromotion(**values)


def test_generic_kernel_refuses_active_without_explicit_promotion() -> None:
    contract = _active_kernel_contract()
    result = BoundedDecisionKernel().evaluate(contract, {"signal": "safe"})

    assert result.result.status is DecisionStatus.REFUSED
    assert result.result.reason == "active_disabled_by_policy"
    assert result.receipt["control"]["promoted"] is False


def test_generic_kernel_requires_all_promotion_evidence() -> None:
    contract = _active_kernel_contract()
    result = BoundedDecisionKernel(
        authority_policy=AuthorityPolicy(
            {
                "policy_version": "test-policy",
                "authority": {"active": {"enabled": True, "minimum_labeled_tasks": 50}},
            }
        )
    ).evaluate(
        contract,
        {"signal": "safe"},
        promotion=_promotion(contract, ci_verified=False, rollback=""),
        caller_authorized=True,
    )

    assert result.result.status is DecisionStatus.REFUSED
    assert "promotion_ci_gate_missing" in result.result.evidence
    assert "promotion_rollback_missing" in result.result.evidence


def test_valid_promotion_is_explicit_and_cache_cannot_bypass_it() -> None:
    contract = _active_kernel_contract()
    kernel = BoundedDecisionKernel(
        cache=DecisionCache(2),
        authority_policy=AuthorityPolicy(
            {
                "policy_version": "test-policy",
                "authority": {"active": {"enabled": True, "minimum_labeled_tasks": 50}},
            }
        ),
    )
    promotion = _promotion(contract)

    active = kernel.evaluate(
        contract, {"signal": "safe"}, promotion=promotion, caller_authorized=True
    )
    refused = kernel.evaluate(contract, {"signal": "safe"})

    assert active.result.status is DecisionStatus.ACCEPTED
    assert active.result.selected == ("local",)
    assert active.receipt["control"]["promoted"] is True
    assert active.receipt["promotion"]["promotion_id"] == promotion.promotion_id
    assert refused.result.status is DecisionStatus.REFUSED
    assert refused.result.reason == "explicit_authority_required"


def test_economy_bridge_active_path_requires_explicit_promotion() -> None:
    contract = ContractRegistry(ROOT).load("routing.data_domain")
    state = DecisionInput("bridge-active", "diagnose", deterministic_available=True)
    generic_contract = build_kernel_contract(contract, mode="active")
    promotion = ActivePromotion(
        promotion_id="promote-routing-v1",
        contract_id=contract.contract_id,
        contract_version=contract.contract_version,
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        rollback="restore-legacy-router",
    )

    result = evaluate_active(
        contract,
        state,
        promotion=promotion,
        authority_policy=AuthorityPolicy(
            {
                "policy_version": "test-policy",
                "authority": {"active": {"enabled": True, "minimum_labeled_tasks": 50}},
            }
        ),
        caller_authorized=True,
    )

    assert result.status.value == "accepted"
    assert result.authority == "active"
    assert result.selected == ("tier_0_deterministic",)
    assert generic_contract.mode == "active"


def test_control_plane_config_keeps_active_disabled_by_default() -> None:
    config = yaml.safe_load(
        (ROOT / "config/decisions/agentic_control_plane.yaml").read_text(encoding="utf-8")
    )

    assert config["authority"]["default_mode"] == "shadow"
    assert config["authority"]["active"]["enabled"] is False
    assert config["authority"]["active"]["minimum_labeled_tasks"] == 50
    assert config["authority"]["active"]["require_ci_gate"] is True
    assert config["authority"]["active"]["require_rollback"] is True
