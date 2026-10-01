from __future__ import annotations

from pathlib import Path

from sparkforge.agentic.shadow import observe_route, route_with_mode
from sparkforge.economy.decision_contracts import ContractRegistry
from sparkforge.economy.decision_models import DecisionInput
from sparkforge.economy.decision_plane import DecisionPlaneService
from sparkforge.economy.decision_receipts import DecisionReceiptStore
from sparkforge.economy.router import CapabilityModelRouter
from sparkforge.registry.models import ExecutionProfile, RiskLevel


def test_runtime_observes_authoritative_router_without_dispatch_side_effect(tmp_path: Path) -> None:
    router = CapabilityModelRouter()
    before = router.route_task(
        "diagnose Glue",
        profile=ExecutionProfile.ECO,
        risk_level=RiskLevel.READ_ONLY,
    )

    observation = observe_route(
        "diagnose Glue",
        repo=tmp_path,
        router=router,
        profile=ExecutionProfile.ECO,
        risk_level=RiskLevel.READ_ONLY,
        task_id="runtime-task",
        service=DecisionPlaneService(
            Path(__file__).resolve().parents[1],
            registry=ContractRegistry(Path(__file__).resolve().parents[1]),
            receipts=DecisionReceiptStore(tmp_path),
        ),
    )

    assert observation.current == before
    assert observation.evaluation.result.receipt_id
    assert observation.current.tier == before.tier


def test_runtime_mode_dispatch_keeps_default_shadow_authoritative(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    service = DecisionPlaneService(
        root,
        registry=ContractRegistry(root),
        receipts=DecisionReceiptStore(tmp_path),
    )
    contract = service.validate("routing.data_domain")
    outcome = route_with_mode(
        DecisionInput("mode-task", "diagnose", deterministic_available=True),
        "tier_3_cheap_local",
        contract=contract,
        repo=root,
        service=service,
        now="fixed",
    )

    assert outcome.promoted is False
    assert outcome.reason == "shadow_mode"
