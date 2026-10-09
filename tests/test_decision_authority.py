from __future__ import annotations

import shutil
from pathlib import Path

from sparkforge_aws.decision import PromotionEvidence
from sparkforge_aws.economy.decision_activation import ActivationEvidence, guard_activation
from sparkforge_aws.economy.decision_contracts import ContractRegistry
from sparkforge_aws.economy.decision_models import AuthorityMode, DecisionInput
from sparkforge_aws.economy.decision_plane import DecisionPlaneService
from sparkforge_aws.economy.decision_receipts import DecisionReceiptStore

ROOT = Path(__file__).resolve().parents[1]


def _assisted_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    contract = repo / "config" / "decisions" / "routing.data_domain.yaml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("mode: shadow", "mode: assisted"),
        encoding="utf-8",
    )
    return repo


def test_assisted_proposes_but_legacy_remains_authority(tmp_path: Path):
    repo = _assisted_repo(tmp_path)
    service = DecisionPlaneService(
        repo,
        registry=ContractRegistry(repo),
        receipts=DecisionReceiptStore(tmp_path / "receipts"),
    )
    outcome = service.assisted(
        DecisionInput("assisted", "diagnose", deterministic_available=True),
        "tier_3_cheap_local",
        contract=service.validate("routing.data_domain"),
        now="fixed",
    )
    assert outcome.promoted is False
    assert outcome.mode == AuthorityMode.ASSISTED.value
    assert outcome.reason == "explicit_authority_required"
    receipt = service.receipts.root / f"{outcome.receipt_id}.json"
    document = service.receipts.verify(receipt)
    assert document["valid"] is True
    payload = receipt.read_text(encoding="utf-8")
    assert '\"authority_decision\"' in payload


def test_assisted_activation_is_supported_without_active_authority():
    decision = guard_activation("assisted", ActivationEvidence(0, False, False))
    assert decision.allowed is True
    assert decision.mode == "assisted"


def test_active_evidence_keeps_explicit_rollback(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    path = repo / "config" / "decisions" / "routing.data_domain.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("mode: shadow", "mode: active"))
    config = repo / "config" / "decisions" / "agentic_control_plane.yaml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("enabled: false", "enabled: true"),
        encoding="utf-8",
    )
    service = DecisionPlaneService(repo)
    contract = service.validate("routing.data_domain")
    outcome = service.active(
        DecisionInput("active-authority", "diagnose", deterministic_available=True),
        "tier_3_cheap_local",
        contract=contract,
        evidence=ActivationEvidence(50, True, True),
        promotion=PromotionEvidence(
            promotion_id="promotion-authority",
            contract_id=contract.contract_id,
            contract_version=contract.contract_version,
            contract_sha256=contract.sha256,
            labeled_tasks=50,
            quality_gate=True,
            economy_gate=True,
            ci_verified=True,
            rollback="restore-shadow",
            evidence_refs=("fixture:active-promotion",),
        ),
        caller_authorized=True,
        now="fixed",
    )
    assert outcome.promoted is True
    assert outcome.rollback_reason == "legacy_router_available"
