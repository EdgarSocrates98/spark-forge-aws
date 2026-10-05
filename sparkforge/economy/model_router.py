"""Provider/model routing independent from case and skill routing."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any


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
    # Capacidade de risco DECLARADA do candidato. `None` nao significa "aguenta
    # tudo": significa que ninguem declarou o limite, e quem decide isso e o
    # scorecard/promotion evidence -- nunca uma inferencia da rota.
    max_risk: int | None = None


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
                    "max_risk": self.selected.max_risk,
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

    def __init__(
        self, candidates: Iterable[ModelCandidate] = (), scorecards: Iterable[ModelScorecard] = ()
    ) -> None:
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
        compatible = [
            candidate for candidate in self.candidates if self._compatible(candidate, request)
        ]
        unresolved: list[str] = []
        if not compatible:
            unresolved.append("no_declared_model_candidate")
            # Diagnostico do que eliminou os candidatos: um vazio sem nome e a
            # mesma classe de recusa silenciosa que o resto do sistema recusa.
            if request.required_reasoning >= 2 and not any(
                "reasoning" in candidate.capabilities for candidate in self.candidates
            ):
                unresolved.append("required_reasoning_unmet")
            if request.risk > 1 and not any(
                candidate.max_risk is not None and candidate.max_risk >= request.risk
                for candidate in self.candidates
            ):
                unresolved.append("risk_capacity_unmet")
            return ModelRouteDecision(
                None,
                mode,
                False,
                "no compatible model",
                len(self.candidates),
                evidence,
                tuple(unresolved),
            )
        selected = max(compatible, key=lambda candidate: self._score(candidate, request))
        if request.context_tokens is not None and selected.max_context_tokens is None:
            unresolved.append("model_context_limit_unresolved")
        if request.risk > 1 and selected.max_risk is None:
            unresolved.append("model_risk_capacity_unresolved")
        if request.required_reasoning >= 2 and "reasoning" not in selected.capabilities:
            unresolved.append("model_reasoning_capacity_unresolved")
        if not selected.cost_known:
            unresolved.append("model_cost_unresolved")
        applied = mode == ModelRouteMode.ACTIVE and active_enabled and authority and bool(evidence)
        if mode == ModelRouteMode.ASSISTED and not authority:
            reason = "assisted route proposed without execution authority"
        elif mode == ModelRouteMode.ACTIVE and not applied:
            reason = (
                "active route refused: enabled, authority and promotion evidence are all required"
            )
        else:
            reason = f"{mode.value} model route selected by declared capability and scorecard"
        return ModelRouteDecision(
            selected, mode, applied, reason, len(self.candidates), evidence, tuple(unresolved)
        )

    def _compatible(self, candidate: ModelCandidate, request: ModelRoutingInput) -> bool:
        if (
            request.context_tokens
            and candidate.max_context_tokens
            and request.context_tokens > candidate.max_context_tokens
        ):
            return False
        if any(tool not in candidate.supported_tools for tool in request.required_tools):
            return False
        # Risco so e limite duro quando a capacidade foi DECLARADA
        # (`max_risk`). Sem declaracao, o candidato nao e eliminado --
        # `model_risk_capacity_unresolved` nomeia a ausencia na decisao.
        if candidate.max_risk is not None and request.risk > candidate.max_risk:
            return False
        # `required_reasoning >= 2` pede capability declarada "reasoning".
        # Requisito sem evidencia de capacidade e incompativel, nao "talvez".
        if request.required_reasoning >= 2 and "reasoning" not in candidate.capabilities:
            return False
        if (
            request.latency_budget_ms is not None
            and candidate.latency_ms is not None
            and candidate.latency_ms > request.latency_budget_ms
        ):
            return False
        if request.budget_usd is not None:
            score = self._scorecard(candidate, request)
            if (
                score is not None
                and score.cost_usd is not None
                and score.cost_usd > request.budget_usd
            ):
                return False
        return True

    def _scorecard(
        self, candidate: ModelCandidate, request: ModelRoutingInput
    ) -> ModelScorecard | None:
        relevant = [
            item
            for item in self.scorecards
            if item.provider == candidate.provider
            and item.model == candidate.model
            and item.task_type == request.task_type
        ]
        return relevant[-1] if relevant else None

    def _score(self, candidate: ModelCandidate, request: ModelRoutingInput) -> tuple[float, ...]:
        """Tupla lexicografica de ranking. Convencao documentada, nao medida:

        `complexity` ajusta a qualidade exigida -- `quality - (complexity - 1) *
        (1 - quality)` -- de modo que modelos fracos pagam mais caro sob
        complexidade alta, e o input finalmente move o ranking (antes entrava
        como constante identica para todo candidato, ou seja: morta).
        `structured_output_reliability` e `failure_rate`, ja declarados no
        scorecard, entram depois de tool correctness e antes de custo.
        """
        score = self._scorecard(candidate, request)
        quality = score.quality if score and score.quality is not None else 0.0
        adjusted_quality = quality - (request.complexity - 1) * (1.0 - quality)
        evidence = (
            score.evidence_correctness if score and score.evidence_correctness is not None else 0.0
        )
        tool = score.tool_correctness if score and score.tool_correctness is not None else 0.0
        structured = (
            score.structured_output_reliability
            if score and score.structured_output_reliability is not None
            else 0.0
        )
        failure = -(score.failure_rate) if score and score.failure_rate is not None else 0.0
        latency = -(candidate.latency_ms or 0.0)
        cost = -(score.cost_usd or 0.0) if score else 0.0
        return (
            adjusted_quality,
            evidence,
            tool,
            structured,
            failure,
            cost,
            latency,
            float(candidate.cost_known),
        )


__all__ = [
    "AdaptiveModelRouter",
    "ModelCandidate",
    "ModelRouteDecision",
    "ModelRouteMode",
    "ModelRoutingInput",
    "ModelScorecard",
]
