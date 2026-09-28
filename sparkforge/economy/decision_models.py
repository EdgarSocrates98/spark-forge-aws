"""Provider-independent contracts for the declarative shadow Decision Plane."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class DecisionStatus(str, Enum):
    ACCEPTED = "accepted"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"
    UNRESOLVED = "unresolved"
    REFUSED = "refused"


class ComparisonState(str, Enum):
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    COVERAGE_GAP = "coverage_gap"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    """Read-only view of the existing case budget."""

    max_total_tokens: int | None = None
    max_tool_calls: int | None = None
    tokens_used: int = 0
    tool_calls_used: int = 0

    def __post_init__(self) -> None:
        values = (
            self.max_total_tokens,
            self.max_tool_calls,
            self.tokens_used,
            self.tool_calls_used,
        )
        if any(value is not None and value < 0 for value in values):
            raise ValueError("budget values must be non-negative")

    def to_dict(self) -> dict[str, int | None]:
        return {
            "max_total_tokens": self.max_total_tokens,
            "max_tool_calls": self.max_tool_calls,
            "tokens_used": self.tokens_used,
            "tool_calls_used": self.tool_calls_used,
        }


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """Provider token usage with mandatory host transcript provenance."""

    input_tokens: int | None
    output_tokens: int | None
    transcript_sha256: str | None
    source: str = "host_transcript"
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        for value in (self.input_tokens, self.output_tokens):
            if value is not None and value < 0:
                raise ValueError("provider token counts must be non-negative")
        if self.resolved and not self.transcript_sha256:
            raise ValueError("resolved provider usage requires transcript_sha256")

    @property
    def resolved(self) -> bool:
        return (
            self.input_tokens is not None
            and self.output_tokens is not None
            and bool(self.transcript_sha256)
            and self.unresolved_reason is None
        )

    @classmethod
    def unresolved(cls, reason: str) -> ProviderUsage:
        return cls(None, None, None, unresolved_reason=reason)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ProviderUsage:
        if "provider_tokens" not in raw:
            return cls.unresolved("host_transcript_absent")
        tokens = raw.get("provider_tokens")
        if tokens is None:
            return cls.unresolved(str(raw.get("unresolved_reason", "host_transcript_absent")))
        if not isinstance(tokens, Mapping):
            return cls.unresolved("provider_tokens_invalid")
        transcript_sha256 = raw.get("transcript_sha256")
        if not isinstance(transcript_sha256, str) or not transcript_sha256.strip():
            return cls.unresolved("transcript_provenance_absent")
        try:
            input_tokens = int(tokens["input_tokens"])
            output_tokens = int(tokens["output_tokens"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("provider_tokens must declare input_tokens and output_tokens") from exc
        return cls(input_tokens, output_tokens, transcript_sha256.strip())

    def to_dict(self) -> dict[str, Any]:
        if not self.resolved:
            return {
                "provider_tokens": None,
                "tokens_unresolved": True,
                "unresolved_reason": self.unresolved_reason or "provider_usage_unresolved",
            }
        return {
            "provider_tokens": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.input_tokens + self.output_tokens,
            },
            "tokens_unresolved": False,
            "source": self.source,
            "transcript_sha256": self.transcript_sha256,
        }


@dataclass(frozen=True, slots=True)
class DecisionInput:
    """Canonical state shared by the runtime bridge and CLI."""

    task_id: str
    task_description: str
    evidence_kinds: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    current_route: str | None = None
    profile: str = "eco"
    risk_level: str = "read_only"
    deterministic_available: bool = False
    cached: bool = False
    budget: BudgetSnapshot = field(default_factory=BudgetSnapshot)
    payload_bytes: int | None = None
    provider_usage: ProviderUsage = field(
        default_factory=lambda: ProviderUsage.unresolved("host_transcript_absent")
    )

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")
        if not self.task_description.strip():
            raise ValueError("task_description must not be empty")
        if self.payload_bytes is not None and self.payload_bytes < 0:
            raise ValueError("payload_bytes must be non-negative")
        object.__setattr__(
            self,
            "evidence_kinds",
            tuple(
                sorted({str(value).strip() for value in self.evidence_kinds if str(value).strip()})
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            tuple(
                sorted({str(value).strip() for value in self.evidence_ids if str(value).strip()})
            ),
        )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> DecisionInput:
        evidence_kinds = raw.get("evidence_kinds", ())
        evidence_ids = raw.get("evidence_ids", ())
        if not isinstance(evidence_kinds, (list, tuple)):
            raise ValueError("evidence_kinds must be an array")
        if not isinstance(evidence_ids, (list, tuple)):
            raise ValueError("evidence_ids must be an array")
        budget_raw = raw.get("budget") or {}
        if not isinstance(budget_raw, Mapping):
            raise ValueError("budget must be an object")
        budget = BudgetSnapshot(
            max_total_tokens=(
                int(budget_raw["max_total_tokens"])
                if budget_raw.get("max_total_tokens") is not None
                else None
            ),
            max_tool_calls=(
                int(budget_raw["max_tool_calls"])
                if budget_raw.get("max_tool_calls") is not None
                else None
            ),
            tokens_used=int(budget_raw.get("tokens_used", 0)),
            tool_calls_used=int(budget_raw.get("tool_calls_used", 0)),
        )
        usage_raw = raw.get("provider_usage")
        usage = (
            ProviderUsage.from_mapping(usage_raw)
            if isinstance(usage_raw, Mapping)
            else ProviderUsage.unresolved("host_transcript_absent")
        )
        return cls(
            task_id=str(raw.get("task_id", "")),
            task_description=str(raw.get("task_description", "")),
            evidence_kinds=tuple(str(value) for value in evidence_kinds),
            evidence_ids=tuple(str(value) for value in evidence_ids),
            current_route=(str(raw["current_route"]) if raw.get("current_route") else None),
            profile=str(raw.get("profile", "eco")),
            risk_level=str(raw.get("risk_level", "read_only")),
            deterministic_available=bool(raw.get("deterministic_available", False)),
            cached=bool(raw.get("cached", False)),
            budget=budget,
            payload_bytes=(
                int(raw["payload_bytes"]) if raw.get("payload_bytes") is not None else None
            ),
            provider_usage=usage,
        )

    def canonical(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "evidence_kinds": list(self.evidence_kinds),
            "evidence_ids": list(self.evidence_ids),
            "current_route": self.current_route,
            "profile": self.profile,
            "risk_level": self.risk_level,
            "deterministic_available": self.deterministic_available,
            "cached": self.cached,
            "budget": self.budget.to_dict(),
            "payload_bytes": self.payload_bytes,
            "provider_usage": self.provider_usage.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DecisionResult:
    contract_id: str
    contract_version: str
    contract_sha256: str
    status: DecisionStatus
    selected: tuple[str, ...]
    confidence: float | None
    confidence_source: str
    method: str
    unresolved: tuple[str, ...] = ()
    budget: BudgetSnapshot = field(default_factory=BudgetSnapshot)
    receipt_id: str | None = None
    fingerprint: str | None = None
    cache_hit: bool = False
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status in {DecisionStatus.UNRESOLVED, DecisionStatus.REFUSED} and self.selected:
            raise ValueError("unresolved and refused results cannot select a route")
        if self.status == DecisionStatus.ACCEPTED and not self.selected:
            raise ValueError("accepted result requires a selected route")

    @classmethod
    def unresolved_result(
        cls, contract: Any, budget: BudgetSnapshot, reason: str
    ) -> DecisionResult:
        return cls(
            contract_id=contract.contract_id,
            contract_version=contract.contract_version,
            contract_sha256=contract.sha256,
            status=DecisionStatus.UNRESOLVED,
            selected=(),
            confidence=None,
            confidence_source="unresolved",
            method="declared_predicates",
            unresolved=(reason,),
            budget=budget,
        )

    @classmethod
    def refused_result(cls, contract: Any, budget: BudgetSnapshot, reason: str) -> DecisionResult:
        return cls(
            contract_id=contract.contract_id,
            contract_version=contract.contract_version,
            contract_sha256=contract.sha256,
            status=DecisionStatus.REFUSED,
            selected=(),
            confidence=None,
            confidence_source="unresolved",
            method="declared_predicates",
            unresolved=(reason,),
            budget=budget,
        )

    def with_receipt(self, receipt_id: str) -> DecisionResult:
        return replace(self, receipt_id=receipt_id)

    def with_kernel(
        self,
        *,
        fingerprint: str | None,
        cache_hit: bool,
        evidence: tuple[str, ...] = (),
    ) -> DecisionResult:
        return replace(
            self,
            fingerprint=fingerprint,
            cache_hit=cache_hit,
            evidence=evidence,
        )

    def to_dict(self, *, include_receipt: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "status": self.status.value,
            "selected": list(self.selected),
            "confidence": self.confidence,
            "confidence_source": self.confidence_source,
            "method": self.method,
            "unresolved": list(self.unresolved),
            "budget": self.budget.to_dict(),
            "fingerprint": self.fingerprint,
            "cache_hit": self.cache_hit,
            "evidence": list(self.evidence),
        }
        if include_receipt:
            result["receipt_id"] = self.receipt_id
        return result


@dataclass(frozen=True, slots=True)
class DecisionComparison:
    state: ComparisonState
    current_route: str | None
    shadow_route: str | None
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "current_route": self.current_route,
            "shadow_route": self.shadow_route,
            "unresolved": list(self.unresolved),
        }


@dataclass(frozen=True, slots=True)
class ShadowEvaluation:
    result: DecisionResult
    comparison: DecisionComparison
    receipt: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result.to_dict(),
            "comparison": self.comparison.to_dict(),
            "receipt": self.receipt.to_dict(),
        }


__all__ = [
    "BudgetSnapshot",
    "ComparisonState",
    "DecisionComparison",
    "DecisionInput",
    "DecisionResult",
    "DecisionStatus",
    "ProviderUsage",
    "ShadowEvaluation",
]
