"""Provider-neutral control plane for explicit route promotion."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from sparkforge.agentic.budget import BudgetExceededError
from sparkforge.agentic.governor import (
    AgentGovernor,
    GovernorDecision,
    GovernorLimits,
    GovernorPolicy,
)
from sparkforge.agentic.recovery import (
    FailureClass,
    RecoveryAction,
    RecoveryDecision,
    RecoveryPolicy,
)
from sparkforge.decision.authority import AuthorityPolicy
from sparkforge.decision.fingerprint import digest
from sparkforge.economy.decision_activation import ActivationEvidence
from sparkforge.economy.decision_contracts import DecisionContract
from sparkforge.economy.decision_models import (
    ActiveRouteOutcome,
    DecisionInput,
)
from sparkforge.economy.decision_plane import DecisionPlaneService


@dataclass(frozen=True, slots=True)
class GovernedRecovery:
    decision: RecoveryDecision
    governor: GovernorDecision
    budget_consumed: bool
    cycle_fingerprint: str = ""
    budget_before: dict[str, Any] | None = None
    budget_after: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": replace(self.decision, budget_consumed=self.budget_consumed).to_dict(),
            "governor": self.governor.to_dict(),
            "budget_consumed": self.budget_consumed,
            "cycle_fingerprint": self.cycle_fingerprint,
            "budget_before": self.budget_before,
            "budget_after": self.budget_after,
        }


class RecoveryGovernor:
    """Resolve recovery through policy, governor and mutable case budget."""

    def __init__(
        self,
        policy: RecoveryPolicy | None = None,
        governor: AgentGovernor | None = None,
    ) -> None:
        self.policy = policy or RecoveryPolicy()
        self.governor = governor or AgentGovernor()
        self._seen_cycles: set[str] = set()

    def resolve(
        self,
        failure: str | FailureClass,
        *,
        attempt: int,
        strategy_fingerprint: str,
        history: tuple[str, ...] = (),
        profile: str = "economy",
        risk: str = "low",
        budget: Any | None = None,
    ) -> GovernedRecovery:
        repeated_cycle = strategy_fingerprint in self._seen_cycles
        decision = self.policy.next(
            failure,
            attempt=attempt,
            strategy_fingerprint=strategy_fingerprint,
            history=tuple(history) + ((strategy_fingerprint,) if repeated_cycle else ()),
        )
        self._seen_cycles.add(strategy_fingerprint)
        needs_retry_budget = decision.action in {
            RecoveryAction.RETRY.value,
            RecoveryAction.REPLAN.value,
        }
        is_retry = decision.action == RecoveryAction.RETRY.value
        is_replan = decision.action == RecoveryAction.REPLAN.value
        status = "accepted" if needs_retry_budget else "unresolved"
        governor_decision = self.governor.resolve(
            profile,
            risk,
            status,
            requested=GovernorLimits(
                1,
                0,
                1 if is_retry else 0,
                1,
                max_replans=1 if is_replan else 0,
            ),
            budget=budget,
        )
        before = _budget_snapshot(budget)
        if needs_retry_budget and governor_decision.refused:
            decision = replace(
                decision,
                action=RecoveryAction.STOP.value,
                reason="governor_recovery_budget_exhausted",
                terminal=True,
            )
            return GovernedRecovery(
                decision,
                governor_decision,
                False,
                strategy_fingerprint,
                before,
                before,
            )
        consumed = False
        if needs_retry_budget and budget is not None:
            consume = getattr(budget, "consume_recovery", None)
            if callable(consume):
                try:
                    consume(decision.action)
                except BudgetExceededError:
                    decision = replace(
                        decision,
                        action=RecoveryAction.STOP.value,
                        reason="case_budget_recovery_exhausted",
                        terminal=True,
                    )
                else:
                    consumed = True
        return GovernedRecovery(
            decision,
            governor_decision,
            consumed,
            strategy_fingerprint,
            before,
            _budget_snapshot(budget),
        )


class AgenticDecisionController:
    """Select shadow or active mode while preserving bounded fallback."""

    def __init__(
        self,
        service: DecisionPlaneService,
        *,
        governor: AgentGovernor | None = None,
        recovery: RecoveryPolicy | None = None,
        authority_policy: AuthorityPolicy | None = None,
    ) -> None:
        self.service = service
        self.governor = governor or AgentGovernor()
        self.recovery = recovery or RecoveryPolicy()
        self.recovery_governor = RecoveryGovernor(self.recovery, self.governor)
        self.authority_policy = authority_policy or service.authority_policy
        if authority_policy is not None:
            service.authority_policy = authority_policy

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
            authority_policy=AuthorityPolicy.from_repo(root),
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
        caller_authorized: bool = False,
    ) -> ActiveRouteOutcome:
        if contract.mode == "active":
            outcome = self.service.active(
                request,
                legacy_route,
                contract=contract,
                evidence=evidence,
                caller_authorized=caller_authorized,
                governor=self.governor,
                now=now,
                trace_ref=trace_ref,
            )
        elif contract.mode == "assisted":
            outcome = self.service.assisted(
                request,
                legacy_route,
                contract=contract,
                caller_authorized=caller_authorized,
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
        if contract.mode == "shadow" or (
            contract.mode == "assisted"
            and outcome.reason in {"legacy_veto", "assisted_non_authoritative"}
        ):
            return outcome
        governed = self.recovery_governor.resolve(
            _failure_class(outcome.reason),
            attempt=attempt,
            strategy_fingerprint=digest(
                {
                    "task_id": request.task_id,
                    "contract_id": contract.contract_id,
                    "failure": outcome.reason,
                    "state": request.canonical(),
                }
            ),
            history=history,
            profile=request.profile,
            risk=request.risk_level,
            budget=request.budget,
        )
        recovery = governed.decision
        recovery_receipt = self.service.receipts.emit_recovery(
            request,
            base_receipt_id=outcome.receipt_id,
            recovery=governed.to_dict(),
            now=now,
        )
        return replace(
            outcome,
            receipt_id=recovery_receipt.receipt_id,
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
    if "timeout" in value:
        return FailureClass.TIMEOUT
    if "transient" in value:
        return FailureClass.TRANSIENT_HOST
    if "strategy" in value or "replan" in value:
        return FailureClass.STRATEGY_REJECTED
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


def _budget_snapshot(budget: Any | None) -> dict[str, Any] | None:
    if budget is None:
        return None
    to_dict = getattr(budget, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        return dict(value) if isinstance(value, dict) else None
    if isinstance(budget, dict):
        return dict(budget)
    return None


__all__ = [
    "AgenticDecisionController",
    "GovernedRecovery",
    "RecoveryGovernor",
    "route_with_fallback",
]
