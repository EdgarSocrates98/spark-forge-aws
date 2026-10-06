"""Deterministic orchestration for bounded decision contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Any

from sparkforge_aws.decision.authority import AuthorityDecision, AuthorityPolicy, PromotionEvidence
from sparkforge_aws.decision.cache import DecisionCache, decision_cache_key
from sparkforge_aws.decision.contracts import DecisionContract
from sparkforge_aws.decision.fingerprint import decision_fingerprint, state_fingerprint
from sparkforge_aws.decision.measurement import payload_bytes
from sparkforge_aws.decision.models import (
    CompiledState,
    DecisionResult,
    DecisionStatus,
    KernelEvaluation,
    LocalMeasurement,
)
from sparkforge_aws.decision.primitives import evaluator_for
from sparkforge_aws.decision.receipts import build_receipt
from sparkforge_aws.decision.state import StateCompiler


@dataclass(frozen=True, slots=True)
class ActivePromotion:
    """Explicit evidence required before the generic kernel may execute active."""

    promotion_id: str
    contract_id: str
    contract_version: str
    labeled_tasks: int
    quality_gate: bool
    economy_gate: bool
    ci_verified: bool
    rollback: str
    contract_sha256: str | None = None
    evidence_refs: tuple[str, ...] = ()
    calibration_version: str = "none"
    candidate_identity: dict[str, Any] | None = None

    def as_evidence(self) -> PromotionEvidence:
        return PromotionEvidence(
            promotion_id=self.promotion_id,
            contract_id=self.contract_id,
            contract_version=self.contract_version,
            contract_sha256=self.contract_sha256,
            labeled_tasks=self.labeled_tasks,
            quality_gate=self.quality_gate,
            economy_gate=self.economy_gate,
            ci_verified=self.ci_verified,
            rollback=self.rollback,
            evidence_refs=self.evidence_refs,
            calibration_version=self.calibration_version,
        )

    def missing_for(
        self, contract: DecisionContract, *, minimum_labeled_tasks: int = 50
    ) -> tuple[str, ...]:
        missing: list[str] = []
        if not self.promotion_id.strip():
            missing.append("promotion_id_missing")
        if self.contract_id != contract.contract_id:
            missing.append("promotion_contract_id_mismatch")
        if self.contract_version != contract.contract_version:
            missing.append("promotion_contract_version_mismatch")
        if self.contract_sha256 is not None and self.contract_sha256 != contract.sha256:
            missing.append("promotion_contract_sha256_mismatch")
        if self.labeled_tasks < minimum_labeled_tasks:
            missing.append(f"promotion_corpus_below_{minimum_labeled_tasks}_labeled_tasks")
        if not self.quality_gate:
            missing.append("promotion_quality_gate_missing")
        if not self.economy_gate:
            missing.append("promotion_economy_gate_missing")
        if not self.ci_verified:
            missing.append("promotion_ci_gate_missing")
        if not self.rollback.strip():
            missing.append("promotion_rollback_missing")
        return tuple(missing)

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "labeled_tasks": self.labeled_tasks,
            "quality_gate": self.quality_gate,
            "economy_gate": self.economy_gate,
            "ci_verified": self.ci_verified,
            "rollback": self.rollback,
            "evidence_refs": list(self.evidence_refs),
            "calibration_version": self.calibration_version,
            "candidate": self.candidate_identity,
        }


class BoundedDecisionKernel:
    """Evaluate one declared contract with explicit bounded outcomes."""

    def __init__(
        self,
        *,
        cache: DecisionCache | None = None,
        compiler: StateCompiler | None = None,
        authority_policy: AuthorityPolicy | None = None,
    ) -> None:
        self.compiler = compiler or StateCompiler()
        self.cache = cache
        self.authority_policy = authority_policy or AuthorityPolicy()

    def evaluate(
        self,
        contract: DecisionContract,
        raw_state: Mapping[str, Any],
        *,
        now: str | None = None,
        promotion: ActivePromotion | None = None,
        authority: AuthorityDecision | None = None,
        caller_authorized: bool = False,
        cache_owner: str = "decision-kernel",
        cache_freshness: str = "fresh",
        risk_profile: str = "none",
        risk_level: str = "none",
    ) -> KernelEvaluation:
        started = perf_counter_ns()
        compiled = self.compiler.compile(contract, raw_state)
        fingerprint = decision_fingerprint(contract, compiled)
        compiled_identity = state_fingerprint(compiled)
        promotion_missing = _promotion_missing(contract, promotion)
        authority_decision = authority or self.authority_policy.authorize_promotion(
            mode=contract.mode,
            contract=contract,
            evidence=promotion.as_evidence() if promotion is not None else None,
            caller_authorized=caller_authorized,
        )
        if contract.mode != "shadow" and not authority_decision.allowed:
            reason = authority_decision.reason or "activation_not_authorized"
            unresolved = authority_decision.unresolved
            if promotion_missing and reason == "promotion_evidence_incomplete":
                reason = ";".join(promotion_missing)
            result = _result(
                contract,
                fingerprint,
                DecisionStatus.REFUSED,
                reason,
                "authority",
                unresolved,
            )
            measurement = _measurement(started, raw_state)
            return KernelEvaluation(
                result,
                build_receipt(
                    result,
                    state_fingerprint=compiled_identity,
                    measurement=measurement,
                    emitted_at=now,
                    mode=contract.mode,
                    promoted=False,
                    rollback_reason="authority_policy_refused",
                    authority=authority_decision.to_dict(),
                    candidate=promotion.candidate_identity if promotion else None,
                ),
                measurement,
            )
        if promotion_missing:
            result = _result(
                contract,
                fingerprint,
                DecisionStatus.REFUSED,
                ";".join(promotion_missing),
                "activation",
            )
            measurement = _measurement(started, raw_state)
            return KernelEvaluation(
                result,
                build_receipt(
                    result,
                    state_fingerprint=compiled_identity,
                    measurement=measurement,
                    emitted_at=now,
                    mode=contract.mode,
                    promoted=False,
                    rollback_reason="active_promotion_required",
                    candidate=promotion.candidate_identity if promotion else None,
                ),
                measurement,
            )
        state_identity = compiled_identity
        cache = self.cache
        cache_key = decision_cache_key(
            contract.sha256,
            state_identity,
            contract.policy_version,
            contract.calibration_version,
            risk_profile,
            risk_level,
        )
        if cache is not None:
            cached = cache.get_key_owned(
                cache_key,
                owner=cache_owner,
                freshness=cache_freshness,
            )
            if cached is not None:
                result = cached.with_cache_hit(True)
                measurement = _measurement(started, raw_state)
                return KernelEvaluation(
                    result,
                    build_receipt(
                        result,
                        state_fingerprint=state_identity,
                        measurement=measurement,
                        emitted_at=now,
                        mode=contract.mode,
                        promoted=contract.mode == "active",
                        rollback_reason=(promotion.rollback if promotion else None),
                        promotion=(promotion.to_dict() if promotion else None),
                        cache_key=cache_key.canonical(),
                        authority=authority_decision.to_dict(),
                        cache_owner=cache_owner,
                        cache_freshness=cache_freshness,
                        cache_capacity=contract.cache_max_entries,
                        candidate=promotion.candidate_identity if promotion else None,
                    ),
                    measurement,
                )
        result = self._evaluate_uncached(contract, compiled, fingerprint, promotion)
        if cache is not None:
            cache.put_key(
                cache_key,
                result,
                owner=cache_owner,
                freshness=cache_freshness,
                capacity=contract.cache_max_entries,
            )
        measurement = _measurement(started, raw_state)
        return KernelEvaluation(
            result,
            build_receipt(
                result,
                state_fingerprint=state_identity,
                measurement=measurement,
                emitted_at=now,
                mode=contract.mode,
                promoted=contract.mode == "active",
                rollback_reason=(promotion.rollback if promotion else None),
                promotion=(promotion.to_dict() if promotion else None),
                cache_key=cache_key.canonical(),
                authority=authority_decision.to_dict(),
                cache_owner=cache_owner,
                cache_freshness=cache_freshness,
                cache_capacity=contract.cache_max_entries,
                candidate=promotion.candidate_identity if promotion else None,
            ),
            measurement,
        )

    @staticmethod
    def _evaluate_uncached(
        contract: DecisionContract,
        state: CompiledState,
        fingerprint: str,
        promotion: ActivePromotion | None,
    ) -> DecisionResult:
        if contract.mode == "active" and _promotion_missing(contract, promotion):
            return _result(
                contract,
                fingerprint,
                DecisionStatus.REFUSED,
                ";".join(_promotion_missing(contract, promotion)),
                "activation",
            )
        if contract.mode not in {"shadow", "assisted", "active"}:
            return _result(
                contract,
                fingerprint,
                DecisionStatus.REFUSED,
                "activation_not_authorized",
                "activation",
            )
        if state.unresolved:
            return _result(
                contract,
                fingerprint,
                DecisionStatus.UNRESOLVED,
                state.unresolved[0],
                "state_compiler",
                state.unresolved,
            )
        outcome = evaluator_for(contract.primitive).evaluate(contract, state.as_dict())
        return _result(
            contract,
            fingerprint,
            outcome.status,
            outcome.reason,
            outcome.method,
            outcome.evidence,
            selected=outcome.selected,
            confidence=outcome.confidence,
        )


def _result(
    contract: DecisionContract,
    fingerprint: str,
    status: DecisionStatus,
    reason: str | None,
    method: str,
    evidence: tuple[str, ...] = (),
    *,
    selected: tuple[str, ...] = (),
    confidence: float | None = None,
) -> DecisionResult:
    return DecisionResult(
        contract.contract_id,
        contract.contract_version,
        contract.sha256,
        fingerprint,
        status,
        selected,
        method,
        confidence,
        reason,
        evidence,
    )


def _measurement(started: int, raw_state: Mapping[str, Any]) -> LocalMeasurement:
    return LocalMeasurement(
        latency_ns=perf_counter_ns() - started,
        payload_bytes=payload_bytes(raw_state),
    )


def _promotion_missing(
    contract: DecisionContract, promotion: ActivePromotion | None
) -> tuple[str, ...]:
    if contract.mode in {"shadow", "assisted"}:
        return ()
    if promotion is None:
        return ("active_promotion_required",)
    return promotion.missing_for(contract)


__all__ = ["ActivePromotion", "BoundedDecisionKernel"]
