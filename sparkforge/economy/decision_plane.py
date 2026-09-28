"""Shared runtime and CLI facade for the shadow Decision Plane.

The economy API remains the compatibility boundary; ``DeterministicDecisionEngine``
delegates evaluation to ``sparkforge.decision`` while this service keeps shadow
comparison, receipt persistence and activation authority unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.economy.decision_activation import (
    ActivationDecision,
    ActivationEvidence,
    guard_activation,
)
from sparkforge.economy.decision_compare import compare_decisions
from sparkforge.economy.decision_contracts import ContractRegistry, DecisionContract
from sparkforge.economy.decision_engine import DeterministicDecisionEngine
from sparkforge.economy.decision_models import DecisionInput, ShadowEvaluation
from sparkforge.economy.decision_receipts import DecisionReceiptStore


class DecisionPlaneService:
    """Orchestrate shadow evaluation without owning execution authority."""

    def __init__(
        self,
        repo: Path | str = ".",
        *,
        registry: ContractRegistry | None = None,
        engine: DeterministicDecisionEngine | None = None,
        receipts: DecisionReceiptStore | None = None,
    ) -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.registry = registry or ContractRegistry(self.repo)
        self.engine = engine or DeterministicDecisionEngine()
        self.receipts = receipts or DecisionReceiptStore(self.repo)

    def validate(self, contract_id: str, version: str | None = None) -> DecisionContract:
        return self.registry.load(contract_id, version)

    def shadow(
        self,
        request: DecisionInput,
        current: Any,
        *,
        contract: DecisionContract,
        now: str | None = None,
        trace_ref: str | None = None,
    ) -> ShadowEvaluation:
        result = self.engine.evaluate(contract, request)
        current_for_compare = current if current is not None else request.current_route
        comparison = compare_decisions(current_for_compare, result)
        receipt = self.receipts.emit(
            request,
            current_for_compare,
            result,
            comparison,
            now=now,
            trace_ref=trace_ref,
        )
        return ShadowEvaluation(result.with_receipt(receipt.receipt_id), comparison, receipt)

    def activation(
        self,
        mode: str,
        *,
        labeled_tasks: int,
        quality_gate: bool,
        economy_gate: bool,
    ) -> ActivationDecision:
        return guard_activation(
            mode,
            ActivationEvidence(labeled_tasks, quality_gate, economy_gate),
        )


def service_for(repo: Path | str = ".") -> DecisionPlaneService:
    return DecisionPlaneService(repo)


__all__ = ["DecisionPlaneService", "service_for"]
