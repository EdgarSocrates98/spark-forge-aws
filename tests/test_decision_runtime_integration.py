from __future__ import annotations

from pathlib import Path

from sparkforge.agentic.shadow import observe_route
from sparkforge.economy.decision_contracts import ContractRegistry
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
