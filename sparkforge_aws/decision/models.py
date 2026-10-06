"""Immutable value objects for the bounded decision kernel."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any


class DecisionStatus(str, Enum):
    ACCEPTED = "accepted"
    ABSTAIN = "abstain"
    UNRESOLVED = "unresolved"
    REFUSED = "refused"


class PrimitiveKind(str, Enum):
    CHOICE = "choice"
    BOOLEAN = "boolean"
    GATE = "gate"
    SCORE = "score"
    ROUTE = "route"
    THRESHOLD = "threshold"


@dataclass(frozen=True, slots=True)
class CompiledState:
    """Canonical state and extraction gaps produced by ``StateCompiler``."""

    values: tuple[tuple[str, Any], ...]
    unresolved: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.values}

    @property
    def resolved(self) -> bool:
        return not self.unresolved


@dataclass(frozen=True, slots=True)
class LocalMeasurement:
    """Local units kept separate from provider tokens and financial cost."""

    latency_ns: int | None
    payload_bytes: int | None
    provider_tokens: dict[str, int] | None = None
    tokens_unresolved: bool = True
    cost_basis: str | None = None

    def __post_init__(self) -> None:
        for value in (self.latency_ns, self.payload_bytes):
            if value is not None and value < 0:
                raise ValueError("local measurement values must be non-negative")
        if self.provider_tokens is not None and self.tokens_unresolved:
            raise ValueError("resolved provider tokens cannot be unresolved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "latency_ns": self.latency_ns,
            "payload_bytes": self.payload_bytes,
            "provider_tokens": self.provider_tokens,
            "tokens_unresolved": self.tokens_unresolved,
            "cost_basis": self.cost_basis,
        }


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    status: DecisionStatus
    selected: tuple[str, ...] = ()
    method: str = "deterministic"
    confidence: float | None = None
    reason: str | None = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status is not DecisionStatus.ACCEPTED and self.selected:
            raise ValueError("only accepted outcomes may select a value")


@dataclass(frozen=True, slots=True)
class DecisionResult:
    contract_id: str
    contract_version: str
    contract_sha256: str
    fingerprint: str
    status: DecisionStatus
    selected: tuple[str, ...]
    method: str
    confidence: float | None
    reason: str | None
    evidence: tuple[str, ...] = ()
    cache_hit: bool = False

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status is not DecisionStatus.ACCEPTED and self.selected:
            raise ValueError("non-accepted results cannot select a value")
        if self.status is DecisionStatus.ACCEPTED and not self.selected:
            raise ValueError("accepted result requires a selection")

    def with_cache_hit(self, cache_hit: bool) -> DecisionResult:
        return replace(self, cache_hit=cache_hit)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "fingerprint": self.fingerprint,
            "status": self.status.value,
            "selected": list(self.selected),
            "method": self.method,
            "confidence": self.confidence,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "cache_hit": self.cache_hit,
        }


@dataclass(frozen=True, slots=True)
class KernelEvaluation:
    result: DecisionResult
    receipt: dict[str, Any]
    measurement: LocalMeasurement

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "result": self.result.to_dict(),
            "receipt": self.receipt,
            "measurement": self.measurement.to_dict(),
        }


__all__ = [
    "CompiledState",
    "DecisionResult",
    "DecisionStatus",
    "EvaluationOutcome",
    "KernelEvaluation",
    "LocalMeasurement",
    "PrimitiveKind",
]
