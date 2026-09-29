from __future__ import annotations

import json
import shutil
from pathlib import Path

from sparkforge.agentic.control import AgenticDecisionController
from sparkforge.decision import FactCache, PromotionEvidence, fact_cache_key
from sparkforge.economy.decision_activation import ActivationEvidence
from sparkforge.economy.decision_contracts import ContractRegistry
from sparkforge.economy.decision_models import BudgetSnapshot, DecisionInput
from sparkforge.economy.decision_plane import DecisionPlaneService
from sparkforge.economy.decision_receipts import DecisionReceiptStore

ROOT = Path(__file__).resolve().parents[1]


def _active_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    contract = repo / "config" / "decisions" / "routing.data_domain.yaml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("mode: shadow", "mode: active"),
        encoding="utf-8",
    )
    policy = repo / "config" / "decisions" / "agentic_control_plane.yaml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace("enabled: false", "enabled: true"),
        encoding="utf-8",
    )
    return repo


def _promotion(contract: object) -> PromotionEvidence:
    return PromotionEvidence(
        promotion_id="jev-promotion",
        contract_id=contract.contract_id,
        contract_version=contract.contract_version,
        contract_sha256=contract.sha256,
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        rollback="restore-shadow",
    )


def test_active_path_promotes_and_receipt_records_rollback(tmp_path: Path) -> None:
    repo = _active_repo(tmp_path)
    service = DecisionPlaneService(
        repo,
        registry=ContractRegistry(repo),
        receipts=DecisionReceiptStore(tmp_path / "receipts"),
    )
    contract = service.validate("routing.data_domain")
    outcome = service.active(
        DecisionInput("active", "diagnose", deterministic_available=True),
        "tier_3_cheap_local",
        contract=contract,
        evidence=ActivationEvidence(50, True, True),
        promotion=_promotion(contract),
        caller_authorized=True,
        now="fixed",
    )

    assert outcome.promoted is True
    assert outcome.route == "tier_0_deterministic"
    assert outcome.fallback_route == "tier_3_cheap_local"
    receipt = json_document(service.receipts.root / f"{outcome.receipt_id}.json")
    assert receipt["control"] == {
        "fallback_reason": None,
        "fallback_route": "tier_3_cheap_local",
        "mode": "active",
        "promoted": True,
        "route": "tier_0_deterministic",
        "rollback_reason": "legacy_router_available",
    }
    assert service.receipts.verify(service.receipts.root / f"{outcome.receipt_id}.json")["valid"]


def test_active_path_falls_back_without_widening_budget(tmp_path: Path) -> None:
    repo = _active_repo(tmp_path)
    service = DecisionPlaneService(repo, receipts=DecisionReceiptStore(tmp_path / "receipts"))
    contract = service.validate("routing.data_domain")
    outcome = service.active(
        DecisionInput(
            "over-budget",
            "diagnose",
            budget=BudgetSnapshot(max_total_tokens=8000, tokens_used=8001),
        ),
        "tier_3_cheap_local",
        contract=contract,
        evidence=ActivationEvidence(50, True, True),
        promotion=_promotion(contract),
        caller_authorized=True,
        now="fixed",
    )

    assert outcome.promoted is False
    assert outcome.route is None
    assert outcome.fallback_route == "tier_3_cheap_local"
    assert "budget_tokens_exceeded" in outcome.unresolved


def test_controller_keeps_shadow_non_authoritative_and_recovery_bounded(tmp_path: Path) -> None:
    service = DecisionPlaneService(
        ROOT,
        receipts=DecisionReceiptStore(tmp_path / "receipts"),
    )
    contract = service.validate("routing.data_domain")
    controller = AgenticDecisionController.from_config(ROOT, service=service)
    outcome = controller.route(
        DecisionInput("shadow", "diagnose", deterministic_available=True),
        "tier_3_cheap_local",
        contract=contract,
        now="fixed",
    )

    assert outcome.promoted is False
    assert outcome.reason == "shadow_mode"
    assert outcome.fallback_route == "tier_3_cheap_local"
    assert outcome.recovery_action == "abstain"


def test_cache_owned_lookup_refuses_stale_record() -> None:
    cache = FactCache()
    key = fact_cache_key("artifact", "extractor-v1", "rules-v1")
    cache.put(key, {"facts": []}, owner="extractor", freshness="stale")

    assert cache.get_owned(key, owner="extractor") is None
    assert cache.stats()["last_invalidation_reason"] == "owner_or_freshness_mismatch"


def json_document(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
