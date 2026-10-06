"""FASE 6 do prompt_evo_runtime: rota adaptativa dentro do Decision Plane.

A costura pedida e `task -> governor -> route -> scorecard -> Decision Plane
-> shadow route`: a decisao do `AdaptiveModelRouter` (ja com scorecard e
maturidade da FASE 5) vira o "current" observado pelo plano declarativo, com
recibo persistido -- e a promocao continua passando pelos gates de autoridade
existentes, nunca por score.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge.agentic.shadow import observe_adaptive_route, route_with_mode
from sparkforge.economy.decision_contracts import ContractRegistry
from sparkforge.economy.decision_models import DecisionInput
from sparkforge.economy.decision_plane import DecisionPlaneService
from sparkforge.economy.decision_receipts import DecisionReceiptStore
from sparkforge.economy.model_router import (
    AdaptiveModelRouter,
    ModelCandidate,
    ModelRoutingInput,
    ModelScorecard,
)

ROOT = Path(__file__).resolve().parents[1]


def _service(tmp_path: Path) -> DecisionPlaneService:
    return DecisionPlaneService(
        ROOT,
        registry=ContractRegistry(ROOT),
        receipts=DecisionReceiptStore(tmp_path),
    )


def _router() -> AdaptiveModelRouter:
    return AdaptiveModelRouter(
        [ModelCandidate(provider="p", model="m", capabilities=("reasoning",))],
        [
            ModelScorecard(
                provider="p",
                model="m",
                task_type="diagnose",
                quality=0.9,
                observations=9,
            )
        ],
    )


class TestAdaptiveNoDecisionPlane:
    def test_rota_adaptativa_vira_current_observada(self, tmp_path):
        observation = observe_adaptive_route(
            ModelRoutingInput(task_type="diagnose"),
            task_description="diagnose Glue job",
            repo=tmp_path,
            service=_service(tmp_path),
            router=_router(),
        )
        assert observation.decision.selected is not None
        assert observation.evaluation.result.receipt_id
        # O plano observou a rota adaptativa como "current", em texto canonico.
        assert observation.evaluation.request.current_route == "p/m"

    def test_health_e_maturidade_acompanham_a_observacao(self, tmp_path):
        observation = observe_adaptive_route(
            ModelRoutingInput(task_type="diagnose"),
            task_description="diagnose Glue job",
            repo=tmp_path,
            service=_service(tmp_path),
            router=_router(),
        )
        assert observation.health["status"] in {
            "ready",
            "partial",
            "degraded",
            "unresolved",
        }
        assert observation.decision.scorecard_maturity == "mature"

    def test_sem_candidato_o_plano_ve_gap_nomeado(self, tmp_path):
        observation = observe_adaptive_route(
            ModelRoutingInput(task_type="diagnose"),
            task_description="diagnose Glue job",
            repo=tmp_path,
            service=_service(tmp_path),
            router=AdaptiveModelRouter(),
        )
        assert "no_declared_model_candidate" in observation.decision.unresolved
        assert observation.evaluation.comparison.state.value == "coverage_gap"


class TestPromocaoContinuaGated:
    def test_contrato_shadow_nao_promove_mesmo_com_score_alto(self, tmp_path):
        service = _service(tmp_path)
        contract = service.validate("routing.data_domain")
        decision = _router().route(ModelRoutingInput(task_type="diagnose"))
        outcome = route_with_mode(
            DecisionInput("task-1", "diagnose Glue job"),
            {"route": "p/m"},
            contract=contract,
            repo=ROOT,
            service=service,
        )
        assert outcome.promoted is False
        assert outcome.reason == "shadow_mode"

    def test_scorecard_maduro_nao_substitui_evidencia_de_promocao(self, tmp_path):
        """Maturidade alta nao e promotion evidence: o outcome do contrato
        shadow segue nao-promovido e o fallback e o legado."""
        service = _service(tmp_path)
        contract = service.validate("routing.data_domain")
        outcome = route_with_mode(
            DecisionInput("task-2", "diagnose Glue job"),
            {"route": "p/m"},
            contract=contract,
            repo=ROOT,
            service=service,
            evidence=None,
        )
        assert outcome.promoted is False
        assert "shadow_mode" in outcome.unresolved
