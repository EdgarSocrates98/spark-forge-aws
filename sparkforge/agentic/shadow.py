"""Opt-in runtime bridge for observing the existing economy router."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.agentic.control import AgenticDecisionController
from sparkforge.economy.decision_activation import ActivationEvidence
from sparkforge.economy.decision_contracts import DecisionContract
from sparkforge.economy.decision_models import (
    ActiveRouteOutcome,
    BudgetSnapshot,
    DecisionInput,
    ProviderUsage,
    ShadowEvaluation,
)
from sparkforge.economy.decision_plane import DecisionPlaneService
from sparkforge.economy.model_router import (
    AdaptiveModelRouter,
    ModelRouteDecision,
    ModelRoutingInput,
)
from sparkforge.economy.router import CapabilityModelRouter, RoutingDecision
from sparkforge.registry.models import ExecutionProfile, RiskLevel


@dataclass(frozen=True, slots=True)
class ShadowRouteObservation:
    current: RoutingDecision
    evaluation: ShadowEvaluation


@dataclass(frozen=True, slots=True)
class AdaptiveRouteObservation:
    """Rota adaptativa observada pelo Decision Plane, com a saude por eixo.

    `decision` e o que o `AdaptiveModelRouter` concluiu (scorecard +
    maturidade); `evaluation` e o que o plano declarativo respondeu sobre o
    mesmo estado. Nenhuma das duas promove nada sozinha.
    """

    decision: ModelRouteDecision
    health: dict[str, Any]
    evaluation: ShadowEvaluation


def route_with_mode(
    request: DecisionInput,
    legacy_route: Any,
    *,
    contract: DecisionContract,
    repo: Path | str = ".",
    service: DecisionPlaneService | None = None,
    evidence: ActivationEvidence | None = None,
    now: str | None = None,
    trace_ref: str | None = None,
) -> ActiveRouteOutcome:
    """Dispatch an explicit contract mode through bounded control policy."""
    plane = service or DecisionPlaneService(repo)
    return AgenticDecisionController.from_config(repo, service=plane).route(
        request,
        legacy_route,
        contract=contract,
        evidence=evidence,
        now=now,
        trace_ref=trace_ref,
    )


def observe_route(
    task_description: str,
    *,
    repo: Path | str = ".",
    contract_id: str = "routing.data_domain",
    profile: ExecutionProfile = ExecutionProfile.ECO,
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    is_deterministic_available: bool = False,
    is_cached: bool = False,
    task_id: str = "runtime-task",
    evidence_kinds: tuple[str, ...] = (),
    evidence_ids: tuple[str, ...] = (),
    budget: BudgetSnapshot | None = None,
    payload_bytes: int | None = None,
    host_usage: dict[str, Any] | None = None,
    router: CapabilityModelRouter | None = None,
    service: DecisionPlaneService | None = None,
) -> ShadowRouteObservation:
    current_router = router or CapabilityModelRouter()
    current = current_router.route_task(
        task_description,
        profile=profile,
        risk_level=risk_level,
        is_deterministic_available=is_deterministic_available,
        is_cached=is_cached,
    )
    usage = _provider_usage(host_usage)
    state = DecisionInput(
        task_id=task_id,
        task_description=task_description,
        evidence_kinds=evidence_kinds,
        evidence_ids=evidence_ids,
        current_route=current.tier.value,
        profile=profile.value,
        risk_level=risk_level.value,
        deterministic_available=is_deterministic_available,
        cached=is_cached,
        budget=budget or BudgetSnapshot(),
        payload_bytes=payload_bytes,
        provider_usage=usage,
    )
    plane = service or DecisionPlaneService(repo)
    contract = plane.validate(contract_id)
    evaluation = plane.shadow(state, current, contract=contract)
    return ShadowRouteObservation(current, evaluation)


def observe_adaptive_route(
    request: ModelRoutingInput,
    *,
    task_description: str,
    repo: Path | str = ".",
    contract_id: str = "routing.data_domain",
    profile: ExecutionProfile = ExecutionProfile.ECO,
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    task_id: str = "runtime-task",
    router: AdaptiveModelRouter | None = None,
    service: DecisionPlaneService | None = None,
    now: str | None = None,
    trace_ref: str | None = None,
) -> AdaptiveRouteObservation:
    """Task -> route -> scorecard -> Decision Plane -> shadow route.

    O `AdaptiveModelRouter` decide em modo SHADOW (a decisao nao aplica nada);
    a rota escolhida entra como `current` na avaliacao do plano, que compara
    contra o contrato declarativo e emite recibo. `provider/model` e a forma
    canonica de rota do adaptativo dentro do plano -- uma tupla legivel,
    nao o dict inteiro da decisao.
    """
    adaptive = router or AdaptiveModelRouter()
    decision = adaptive.route(request)
    health = adaptive.route_health(request)
    selected = decision.selected
    current = f"{selected.provider}/{selected.model}" if selected else None
    state = DecisionInput(
        task_id=task_id,
        task_description=task_description,
        current_route=current,
        profile=profile.value,
        risk_level=risk_level.value,
        provider_usage=ProviderUsage.unresolved("host_transcript_absent"),
    )
    plane = service or DecisionPlaneService(repo)
    contract = plane.validate(contract_id)
    evaluation = plane.shadow(
        state, current, contract=contract, now=now, trace_ref=trace_ref
    )
    return AdaptiveRouteObservation(decision, health, evaluation)


def _provider_usage(host_usage: dict[str, Any] | None) -> ProviderUsage:
    if not host_usage:
        return ProviderUsage.unresolved("host_transcript_absent")
    try:
        return ProviderUsage.from_mapping(host_usage)
    except ValueError:
        return ProviderUsage.unresolved("provider_tokens_invalid")


__all__ = [
    "AdaptiveRouteObservation",
    "ShadowRouteObservation",
    "observe_adaptive_route",
    "observe_route",
    "route_with_mode",
]
