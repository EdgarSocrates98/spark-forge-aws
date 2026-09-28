"""Provider-neutral control plane for explicit route promotion."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from sparkforge.agentic.governor import AgentGovernor, GovernorPolicy
from sparkforge.agentic.recovery import FailureClass, RecoveryPolicy
from sparkforge.economy.decision_activation import ActivationEvidence
from sparkforge.economy.decision_contracts import DecisionContract
from sparkforge.economy.decision_models import (
    ActiveRouteOutcome,
    DecisionInput,
)
from sparkforge.economy.decision_plane import DecisionPlaneService


class AgenticDecisionController:
    """Select shadow or active mode while preserving bounded fallback."""

    def __init__(
        self,
        service: DecisionPlaneService,
        *,
        governor: AgentGovernor | None = None,
        recovery: RecoveryPolicy | None = None,
    ) -> None:
        self.service = service
        self.governor = governor or AgentGovernor()
        self.recovery = recovery or RecoveryPolicy()

    @classmethod
    def from_config(
        cls,
        repo: Path | str = ".",
        *,
        service: DecisionPlaneService | None = None,
    ) -> AgenticDecisionController:
        root = Path(repo).expanduser().resolve()
        path = root / "config" / "decisions" / "agentic_control_plane.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("agentic control policy must be a mapping")
        return cls(
            service or DecisionPlaneService(root),
            governor=AgentGovernor(GovernorPolicy.from_mapping(raw)),
            recovery=RecoveryPolicy.from_mapping(raw),
        )

    def route(
        self,
        request: DecisionInput,
        legacy_route: Any,
        *,
        contract: DecisionContract,
        evidence: ActivationEvidence | None = None,
        now: str | None = None,
        trace_ref: str | None = None,
        attempt: int = 0,
        history: tuple[str, ...] = (),
    ) -> ActiveRouteOutcome:
        if contract.mode == "active":
            outcome = self.service.active(
                request,
                legacy_route,
                contract=contract,
                evidence=evidence,
                governor=self.governor,
                now=now,
                trace_ref=trace_ref,
            )
        else:
            evaluation = self.service.shadow(
                request,
                legacy_route,
                contract=contract,
                now=now,
                trace_ref=trace_ref,
            )
            outcome = ActiveRouteOutcome(
                promoted=False,
                route=None,
                fallback_route=_route_value(legacy_route),
                reason="shadow_mode",
                receipt_id=evaluation.receipt.receipt_id,
                mode="shadow",
                status=evaluation.result.status.value,
                confidence=evaluation.result.confidence,
                evidence=evaluation.result.evidence,
                rollback_reason="legacy_router_authoritative",
                unresolved=("shadow_mode",),
            )
        if outcome.promoted:
            return outcome
        recovery = self.recovery.next(
            _failure_class(outcome.reason),
            attempt=attempt,
            strategy_fingerprint=outcome.receipt_id,
            history=history,
        )
        return replace(
            outcome,
            recovery_action=recovery.action,
            recovery_reason=recovery.reason,
        )


def route_with_fallback(
    service: DecisionPlaneService,
    request: DecisionInput,
    legacy_route: Any,
    *,
    contract: DecisionContract,
    evidence: ActivationEvidence | None = None,
    governor: AgentGovernor | None = None,
    recovery: RecoveryPolicy | None = None,
    now: str | None = None,
    trace_ref: str | None = None,
) -> ActiveRouteOutcome:
    """Route through the control plane and retain legacy fallback."""
    return AgenticDecisionController(
        service,
        governor=governor,
        recovery=recovery,
    ).route(
        request,
        legacy_route,
        contract=contract,
        evidence=evidence,
        now=now,
        trace_ref=trace_ref,
    )


def _failure_class(reason: str | None) -> FailureClass:
    value = (reason or "missing_evidence").lower()
    if "budget" in value or "governor" in value:
        return FailureClass.BUDGET_EXCEEDED
    if "invalid" in value or "schema" in value:
        return FailureClass.INVALID_INPUT
    if "conflict" in value or "disagreement" in value:
        return FailureClass.DETERMINISTIC_CONFLICT
    return FailureClass.MISSING_EVIDENCE


def _route_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        route = value.get("route") or value.get("selected")
        if isinstance(route, (list, tuple)):
            route = route[0] if route else None
        return str(route).strip() if route else None
    tier = getattr(value, "tier", None)
    return str(getattr(tier, "value", tier)).strip() if tier is not None else None


__all__ = ["AgenticDecisionController", "route_with_fallback"]
