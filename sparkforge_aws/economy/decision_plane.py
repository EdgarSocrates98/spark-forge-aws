"""Shared runtime and CLI facade for the shadow Decision Plane.

The economy API remains the compatibility boundary; ``DeterministicDecisionEngine``
delegates evaluation to ``sparkforge_aws.decision`` while this service keeps shadow
comparison, receipt persistence and activation authority unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sparkforge_aws.agentic.governor import AgentGovernor, GovernorLimits
from sparkforge_aws.decision.authority import AuthorityDecision, AuthorityPolicy, PromotionEvidence
from sparkforge_aws.decision.runtime import ActivePromotion
from sparkforge_aws.economy.decision_activation import (
    ActivationDecision,
    ActivationEvidence,
    guard_activation,
)
from sparkforge_aws.economy.decision_compare import compare_decisions
from sparkforge_aws.economy.decision_contracts import ContractRegistry, DecisionContract
from sparkforge_aws.economy.decision_engine import DeterministicDecisionEngine
from sparkforge_aws.economy.decision_kernel_bridge import build_kernel_contract, evaluate_active
from sparkforge_aws.economy.decision_models import (
    ActiveRouteOutcome,
    AuthorityMode,
    ComparisonState,
    DecisionComparison,
    DecisionInput,
    DecisionResult,
    DecisionStatus,
    ShadowEvaluation,
)
from sparkforge_aws.economy.decision_receipts import DecisionReceiptStore


class DecisionPlaneService:
    """Orchestrate shadow evaluation without owning execution authority."""

    def __init__(
        self,
        repo: Path | str = ".",
        *,
        registry: ContractRegistry | None = None,
        engine: DeterministicDecisionEngine | None = None,
        receipts: DecisionReceiptStore | None = None,
        authority_policy: AuthorityPolicy | None = None,
    ) -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.registry = registry or ContractRegistry(self.repo)
        self.engine = engine or DeterministicDecisionEngine()
        self.receipts = receipts or DecisionReceiptStore(self.repo)
        self.authority_policy = authority_policy or AuthorityPolicy.from_repo(self.repo)

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
        result = self.engine.evaluate(contract, request).with_authority(AuthorityMode.SHADOW)
        authority = self.authority_policy.authorize_promotion(
            mode=AuthorityMode.SHADOW.value,
            contract=contract,
        )
        current_for_compare = current if current is not None else request.current_route
        comparison = compare_decisions(current_for_compare, result)
        receipt = self.receipts.emit(
            request,
            current_for_compare,
            result,
            comparison,
            now=now,
            trace_ref=trace_ref,
            authority=AuthorityMode.SHADOW.value,
            authority_decision=authority.to_dict(),
        )
        return ShadowEvaluation(
            result.with_receipt(receipt.receipt_id), comparison, receipt, request
        )

    def assisted(
        self,
        request: DecisionInput,
        legacy_route: Any,
        *,
        contract: DecisionContract,
        caller_authorized: bool = False,
        now: str | None = None,
        trace_ref: str | None = None,
    ) -> ActiveRouteOutcome:
        """Offer a bounded proposal only after explicit caller authority."""
        authority = self.authority_policy.authorize_promotion(
            mode=AuthorityMode.ASSISTED.value,
            contract=contract,
            caller_authorized=caller_authorized,
        )
        if not authority.allowed:
            result = DecisionResult.refused_result(
                contract, request.budget, authority.reason or "assisted_authority_refused"
            )
            return self._fallback_outcome(
                request,
                legacy_route,
                contract,
                result,
                (authority.reason or "assisted_authority_refused",),
                now=now,
                trace_ref=trace_ref,
                authority=authority,
            )
        result = self.engine.evaluate(contract, request).with_authority(AuthorityMode.ASSISTED)
        comparison = compare_decisions(legacy_route, result)
        vetoed = comparison.state is not ComparisonState.AGREEMENT
        reason = "legacy_veto" if vetoed else "assisted_non_authoritative"
        receipt = self.receipts.emit(
            request,
            legacy_route,
            result,
            comparison,
            now=now,
            trace_ref=trace_ref,
            mode=AuthorityMode.ASSISTED.value,
            promoted=False,
            fallback_route=_route_value(legacy_route),
            rollback_reason="legacy_router_authoritative",
            fallback_reason=reason,
            authority=AuthorityMode.ASSISTED.value,
            vetoed=vetoed,
            authority_decision=authority.to_dict(),
        )
        return ActiveRouteOutcome(
            promoted=False,
            route=None,
            fallback_route=_route_value(legacy_route),
            reason=reason,
            receipt_id=receipt.receipt_id,
            mode=AuthorityMode.ASSISTED.value,
            status=result.status.value,
            confidence=result.confidence,
            evidence=result.evidence,
            rollback_reason="legacy_router_authoritative",
            unresolved=(reason,),
        )

    def active(
        self,
        request: DecisionInput,
        legacy_route: Any,
        *,
        contract: DecisionContract,
        evidence: ActivationEvidence | None = None,
        activation_evidence: ActivationEvidence | None = None,
        labeled_tasks: int = 0,
        quality_gate: bool = False,
        economy_gate: bool = False,
        promotion: PromotionEvidence | Mapping[str, Any] | Any | None = None,
        caller_authorized: bool = False,
        governor: AgentGovernor | None = None,
        now: str | None = None,
        trace_ref: str | None = None,
    ) -> ActiveRouteOutcome:
        """Promote an active contract only after every gate is satisfied."""
        if evidence is not None and activation_evidence is not None:
            raise ValueError("provide only one activation evidence value")
        selected_evidence = evidence or activation_evidence or ActivationEvidence(
            labeled_tasks, quality_gate, economy_gate
        )
        if contract.mode != "active":
            result = DecisionResult.refused_result(
                contract, request.budget, "active_mode_not_enabled"
            )
            return self._fallback_outcome(
                request,
                legacy_route,
                contract,
                result,
                ("active_mode_not_enabled",),
                now=now,
                trace_ref=trace_ref,
            )
        selected_promotion = PromotionEvidence.from_value(promotion)
        if promotion is None:
            selected_promotion = PromotionEvidence(
                contract_id=contract.contract_id,
                contract_version=contract.contract_version,
                contract_sha256=contract.sha256,
                labeled_tasks=selected_evidence.labeled_tasks,
                quality_gate=selected_evidence.quality_gate,
                economy_gate=selected_evidence.economy_gate,
            )
        authority = self.authority_policy.authorize_promotion(
            mode=contract.mode,
            contract=contract,
            evidence=selected_promotion,
            caller_authorized=caller_authorized,
        )
        if not authority.allowed:
            result = DecisionResult.refused_result(
                contract, request.budget, authority.reason or "active_authority_refused"
            )
            return self._fallback_outcome(
                request,
                legacy_route,
                contract,
                result,
                (authority.reason or "active_authority_refused",) + authority.unresolved,
                now=now,
                trace_ref=trace_ref,
                authority=authority,
            )
        kernel_contract = build_kernel_contract(contract, mode="active")
        kernel_promotion = _kernel_promotion(kernel_contract, selected_promotion)
        result = evaluate_active(
            contract,
            request,
            promotion=kernel_promotion,
            authority_policy=self.authority_policy,
            caller_authorized=True,
        )
        try:
            governor_decision = (governor or AgentGovernor()).resolve(
                request.profile,
                request.risk_level,
                _governor_status(result.status),
                requested=GovernorLimits(
                    max_agents=1,
                    max_debates=0,
                    max_retries=0,
                    max_tokens=contract.budget.max_total_tokens or 0,
                ),
                budget=request.budget,
            )
        except (KeyError, ValueError):
            refused = DecisionResult.refused_result(
                contract, request.budget, "governor_profile_or_risk_invalid"
            ).with_kernel(
                fingerprint=result.fingerprint,
                cache_hit=result.cache_hit,
                evidence=result.evidence,
            )
            return self._fallback_outcome(
                request,
                legacy_route,
                contract,
                refused,
                ("governor_profile_or_risk_invalid",),
                now=now,
                trace_ref=trace_ref,
                authority=authority,
            )
        if result.status is not DecisionStatus.ACCEPTED:
            return self._fallback_outcome(
                request,
                legacy_route,
                contract,
                result,
                result.unresolved or ("decision_not_promotable",),
                now=now,
                trace_ref=trace_ref,
                authority=authority,
            )
        if governor_decision.refused:
            refused = DecisionResult.refused_result(
                contract, request.budget, governor_decision.limits.reason or "governor_refused"
            ).with_kernel(
                fingerprint=result.fingerprint,
                cache_hit=result.cache_hit,
                evidence=result.evidence,
            )
            return self._fallback_outcome(
                request,
                legacy_route,
                contract,
                refused,
                (governor_decision.limits.reason or "governor_refused",),
                now=now,
                trace_ref=trace_ref,
                authority=authority,
            )
        comparison = compare_decisions(legacy_route, result)
        receipt = self.receipts.emit(
            request,
            legacy_route,
            result,
            comparison,
            now=now,
            trace_ref=trace_ref,
            mode="active",
            promoted=True,
            fallback_route=_route_value(legacy_route),
            rollback_reason="legacy_router_available",
            authority=AuthorityMode.ACTIVE.value,
            activation_evidence={
                "labeled_tasks": selected_evidence.labeled_tasks,
                "quality_gate": selected_evidence.quality_gate,
                "economy_gate": selected_evidence.economy_gate,
            },
            authority_decision=authority.to_dict(),
        )
        promoted = result.with_authority(AuthorityMode.ACTIVE).with_receipt(receipt.receipt_id)
        return ActiveRouteOutcome(
            promoted=True,
            route=promoted.selected[0],
            fallback_route=_route_value(legacy_route),
            reason=None,
            receipt_id=receipt.receipt_id,
            status=promoted.status.value,
            confidence=promoted.confidence,
            evidence=promoted.evidence,
            rollback_reason="legacy_router_available",
        )

    def promote(
        self,
        evaluation: ShadowEvaluation,
        *,
        legacy_route: Any,
        promotion: PromotionEvidence | Mapping[str, Any] | Any | None = None,
        caller_authorized: bool = False,
        now: str | None = None,
        trace_ref: str | None = None,
    ) -> ActiveRouteOutcome:
        """Re-emit a successful evaluation as an explicit active promotion."""
        if evaluation.request is None:
            raise ValueError("promotion requires evaluation request")
        if evaluation.result.status is not DecisionStatus.ACCEPTED:
            return self._fallback_outcome(
                evaluation.request,
                legacy_route,
                self.validate(evaluation.result.contract_id, evaluation.result.contract_version),
                evaluation.result,
                evaluation.result.unresolved or ("decision_not_promotable",),
                now=now,
                trace_ref=trace_ref,
            )
        contract = self.validate(evaluation.result.contract_id, evaluation.result.contract_version)
        authority = self.authority_policy.authorize_promotion(
            mode=AuthorityMode.ACTIVE.value,
            contract=contract,
            evidence=promotion,
            caller_authorized=caller_authorized,
        )
        if not authority.allowed:
            return self._fallback_outcome(
                evaluation.request,
                legacy_route,
                contract,
                evaluation.result,
                (authority.reason or "active_authority_refused",) + authority.unresolved,
                now=now,
                trace_ref=trace_ref,
                authority=authority,
            )
        kernel_contract = build_kernel_contract(contract, mode="active")
        kernel_promotion = _kernel_promotion(
            kernel_contract, PromotionEvidence.from_value(promotion)
        )
        result = evaluate_active(
            contract,
            evaluation.request,
            promotion=kernel_promotion,
            authority_policy=self.authority_policy,
            caller_authorized=True,
        )
        if result.status is not DecisionStatus.ACCEPTED:
            return self._fallback_outcome(
                evaluation.request,
                legacy_route,
                contract,
                result,
                result.unresolved or ("decision_not_promotable",),
                now=now,
                trace_ref=trace_ref,
                authority=authority,
            )
        comparison = compare_decisions(legacy_route, result)
        receipt = self.receipts.emit(
            evaluation.request,
            legacy_route,
            result,
            comparison,
            now=now,
            trace_ref=trace_ref,
            mode="active",
            promoted=True,
            fallback_route=_route_value(legacy_route),
            rollback_reason="legacy_router_available",
            authority=AuthorityMode.ACTIVE.value,
            authority_decision=authority.to_dict(),
        )
        result = result.with_authority(AuthorityMode.ACTIVE).with_receipt(
            receipt.receipt_id
        )
        return ActiveRouteOutcome(
            True,
            result.selected[0],
            _route_value(legacy_route),
            None,
            receipt.receipt_id,
            status=result.status.value,
            confidence=result.confidence,
            evidence=result.evidence,
            rollback_reason="legacy_router_available",
        )

    def fallback(
        self,
        request: DecisionInput,
        legacy_route: Any,
        *,
        contract: DecisionContract,
        reason: str,
        result: DecisionResult | None = None,
        now: str | None = None,
        trace_ref: str | None = None,
    ) -> ActiveRouteOutcome:
        """Record a named fallback while retaining the legacy route."""
        decision = result or DecisionResult.refused_result(contract, request.budget, reason)
        return self._fallback_outcome(
            request,
            legacy_route,
            contract,
            decision,
            (reason,),
            now=now,
            trace_ref=trace_ref,
        )

    def _fallback_outcome(
        self,
        request: DecisionInput,
        legacy_route: Any,
        contract: DecisionContract,
        result: DecisionResult,
        reasons: tuple[str, ...],
        *,
        now: str | None,
        trace_ref: str | None,
        authority: AuthorityDecision | None = None,
    ) -> ActiveRouteOutcome:
        current_route = _route_value(legacy_route)
        comparison = DecisionComparison(
            state=ComparisonState.COVERAGE_GAP,
            current_route=current_route,
            shadow_route=None,
            unresolved=reasons,
        )
        receipt = self.receipts.emit(
            request,
            legacy_route,
            result,
            comparison,
            now=now,
            trace_ref=trace_ref,
            mode=contract.mode,
            promoted=False,
            fallback_route=current_route,
            rollback_reason="legacy_router_authoritative",
            fallback_reason=";".join(reasons),
            authority_decision=authority.to_dict() if authority else None,
        )
        return ActiveRouteOutcome(
            promoted=False,
            route=None,
            fallback_route=current_route,
            reason=";".join(reasons),
            receipt_id=receipt.receipt_id,
            mode=contract.mode,
            status=result.status.value,
            confidence=result.confidence,
            evidence=result.evidence,
            rollback_reason="legacy_router_authoritative",
            unresolved=reasons,
        )

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


def _governor_status(status: DecisionStatus) -> str:
    return "accepted" if status is DecisionStatus.ACCEPTED else "unresolved"


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
    if tier is not None:
        return str(getattr(tier, "value", tier)).strip() or None
    return None


def _kernel_promotion(contract: Any, evidence: PromotionEvidence) -> ActivePromotion:
    return ActivePromotion(
        promotion_id=evidence.promotion_id,
        contract_id=contract.contract_id,
        contract_version=contract.contract_version,
        labeled_tasks=evidence.labeled_tasks,
        quality_gate=evidence.quality_gate,
        economy_gate=evidence.economy_gate,
        ci_verified=evidence.ci_verified,
        rollback=evidence.rollback,
        contract_sha256=contract.sha256,
        evidence_refs=evidence.evidence_refs,
        calibration_version=contract.calibration_version,
    )
