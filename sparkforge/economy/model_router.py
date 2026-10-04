"""Provider/model routing independent from case and skill routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class ModelRouteMode(str, Enum):
    SHADOW = "shadow"
    ASSISTED = "assisted"
    ACTIVE = "active"


@dataclass(frozen=True, slots=True)
class ModelScorecard:
    provider: str
    model: str
    task_type: str
    quality: float | None = None
    tool_correctness: float | None = None
    evidence_correctness: float | None = None
    latency_ms: float | None = None
    cost_usd: float | None = None
    failure_rate: float | None = None
    structured_output_reliability: float | None = None
    observations: int = 0


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    provider: str
    model: str
    capabilities: tuple[str, ...] = ()
    supported_tools: tuple[str, ...] = ()
    max_context_tokens: int | None = None
    cost_known: bool = False
    latency_ms: float | None = None


@dataclass(frozen=True, slots=True)
class ModelRoutingInput:
    task_type: str
    complexity: int = 1
    risk: int = 1
    required_reasoning: int = 1
    context_tokens: int | None = None
    required_tools: tuple[str, ...] = ()
    budget_usd: float | None = None
    latency_budget_ms: float | None = None


@dataclass(frozen=True, slots=True)
class ModelRouteDecision:
    selected: ModelCandidate | None
    mode: ModelRouteMode
    applied: bool
    reason: str
    candidates_considered: int
    promotion_evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": (
                {
                    "provider": self.selected.provider,
                    "model": self.selected.model,
                    "capabilities": list(self.selected.capabilities),
                    "supported_tools": list(self.selected.supported_tools),
                    "max_context_tokens": self.selected.max_context_tokens,
                    "cost_known": self.selected.cost_known,
                    "latency_ms": self.selected.latency_ms,
                }
                if self.selected
                else None
            ),
            "mode": self.mode.value,
            "applied": self.applied,
            "reason": self.reason,
            "candidates_considered": self.candidates_considered,
            "promotion_evidence": list(self.promotion_evidence),
            "unresolved": list(self.unresolved),
        }


class AdaptiveModelRouter:
    """Ranks declared candidates; does not call providers or mutate policy."""

    def __init__(self, candidates: Iterable[ModelCandidate] = (), scorecards: Iterable[ModelScorecard] = ()) -> None:
        self.candidates = tuple(candidates)
        self.scorecards = tuple(scorecards)

    def route(
        self,
        request: ModelRoutingInput,
        *,
        mode: ModelRouteMode = ModelRouteMode.SHADOW,
        active_enabled: bool = False,
        authority: bool = False,
        promotion_evidence: Iterable[str] = (),
    ) -> ModelRouteDecision:
        evidence = tuple(str(value) for value in promotion_evidence)
        compatible = [candidate for candidate in self.candidates if self._compatible(candidate, request)]
        unresolved: list[str] = []
        if not compatible:
            unresolved.append("no_declared_model_candidate")
            return ModelRouteDecision(None, mode, False, "no compatible model", len(self.candidates), evidence, tuple(unresolved))
        selected = max(compatible, key=lambda candidate: self._score(candidate, request))
        if request.context_tokens is not None and selected.max_context_tokens is None:
            unresolved.append("model_context_limit_unresolved")
        if not selected.cost_known:
            unresolved.append("model_cost_unresolved")
        applied = mode == ModelRouteMode.ACTIVE and active_enabled and authority and bool(evidence)
        if mode == ModelRouteMode.ASSISTED and not authority:
            reason = "assisted route proposed without execution authority"
        elif mode == ModelRouteMode.ACTIVE and not applied:
            reason = "active route refused: enabled, authority and promotion evidence are all required"
        else:
            reason = f"{mode.value} model route selected by declared capability and scorecard"
        return ModelRouteDecision(selected, mode, applied, reason, len(self.candidates), evidence, tuple(unresolved))

    def _compatible(self, candidate: ModelCandidate, request: ModelRoutingInput) -> bool:
        if request.context_tokens and candidate.max_context_tokens and request.context_tokens > candidate.max_context_tokens:
            return False
        if any(tool not in candidate.supported_tools for tool in request.required_tools):
            return False
        if request.latency_budget_ms is not None and candidate.latency_ms is not None and candidate.latency_ms > request.latency_budget_ms:
            return False
        return True

    def _score(self, candidate: ModelCandidate, request: ModelRoutingInput) -> tuple[float, ...]:
        relevant = [item for item in self.scorecards if item.provider == candidate.provider and item.model == candidate.model and item.task_type == request.task_type]
        score = relevant[-1] if relevant else None
        quality = score.quality if score and score.quality is not None else 0.0
        evidence = score.evidence_correctness if score and score.evidence_correctness is not None else 0.0
        tool = score.tool_correctness if score and score.tool_correctness is not None else 0.0
        latency = -(candidate.latency_ms or 0.0)
        return (quality, evidence, tool, -float(request.complexity), latency, float(candidate.cost_known))


__all__ = [
    "AdaptiveModelRouter",
    "ModelCandidate",
    "ModelRouteDecision",
    "ModelRouteMode",
    "ModelRoutingInput",
    "ModelScorecard",
]
