"""Deterministic orchestration for bounded decision contracts."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter_ns
from typing import Any

from sparkforge.decision.cache import DecisionCache, decision_cache_key
from sparkforge.decision.contracts import DecisionContract
from sparkforge.decision.fingerprint import decision_fingerprint, state_fingerprint
from sparkforge.decision.measurement import payload_bytes
from sparkforge.decision.models import (
    CompiledState,
    DecisionResult,
    DecisionStatus,
    KernelEvaluation,
    LocalMeasurement,
)
from sparkforge.decision.primitives import evaluator_for
from sparkforge.decision.receipts import build_receipt
from sparkforge.decision.state import StateCompiler


class BoundedDecisionKernel:
    """Evaluate one declared contract with explicit bounded outcomes."""

    def __init__(
        self, *, cache: DecisionCache | None = None, compiler: StateCompiler | None = None
    ) -> None:
        self.compiler = compiler or StateCompiler()
        self.cache = cache

    def evaluate(
        self,
        contract: DecisionContract,
        raw_state: Mapping[str, Any],
        *,
        now: str | None = None,
    ) -> KernelEvaluation:
        started = perf_counter_ns()
        compiled = self.compiler.compile(contract, raw_state)
        fingerprint = decision_fingerprint(contract, compiled)
        state_identity = state_fingerprint(compiled)
        cache = self.cache
        cache_key = decision_cache_key(
            contract.sha256,
            state_identity,
            contract.policy_version,
            contract.calibration_version,
        )
        if cache is not None:
            cache.limit_to(contract.cache_max_entries)
            cached = cache.get_key(cache_key)
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
                        cache_key=cache_key.canonical(),
                    ),
                    measurement,
                )
        result = self._evaluate_uncached(contract, compiled, fingerprint)
        if cache is not None:
            cache.put_key(cache_key, result)
        measurement = _measurement(started, raw_state)
        return KernelEvaluation(
            result,
            build_receipt(
                result,
                state_fingerprint=state_identity,
                measurement=measurement,
                emitted_at=now,
                cache_key=cache_key.canonical(),
            ),
            measurement,
        )

    @staticmethod
    def _evaluate_uncached(
        contract: DecisionContract,
        state: CompiledState,
        fingerprint: str,
    ) -> DecisionResult:
        if contract.mode != "shadow":
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


__all__ = ["BoundedDecisionKernel"]
