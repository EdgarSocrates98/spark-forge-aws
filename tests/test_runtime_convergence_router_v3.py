"""FASE 5 do prompt_evo_runtime: Model Router v3 -- scorecard maturity e
route health.

Dois eixos que o prompt pede explicitamente:
- "scorecard maturity" (§32, §143): quantas observacoes sustentam o
  scorecard que rankeou o candidato -- e decisao sem scorecard NAO e
  decisao com scorecard fraco, e "sem evidencia de qualidade".
- `RouteHealth` (§32) com estados por eixo (§144: READY/PARTIAL/DEGRADED/
  UNRESOLVED), nunca um numero 0-100.

Promocao continua exigindo autoridade + evidencia + modo ACTIVE (§33) --
score sozinho nao promove ninguem.
"""

from __future__ import annotations

from sparkforge.adapters._core import agentic_doctor
from sparkforge.economy.model_router import (
    AdaptiveModelRouter,
    ModelCandidate,
    ModelRouteMode,
    ModelRoutingInput,
    ModelScorecard,
)


def _candidate(**kw):
    base = {"provider": "p", "model": "m", "capabilities": ("reasoning",)}
    base.update(kw)
    return ModelCandidate(**base)


def _scorecard(**kw):
    base = {"provider": "p", "model": "m", "task_type": "t", "quality": 0.9}
    base.update(kw)
    return ModelScorecard(**base)


class TestScorecardMaturity:
    def test_sem_scorecard_a_decisao_diz_ausente(self):
        router = AdaptiveModelRouter([_candidate()])
        decision = router.route(ModelRoutingInput(task_type="t"))
        assert decision.scorecard_maturity == "absent"
        assert "scorecard_absent" in decision.unresolved

    def test_scorecard_sem_observacao_e_cold(self):
        router = AdaptiveModelRouter(
            [_candidate()], [_scorecard(observations=0)]
        )
        decision = router.route(ModelRoutingInput(task_type="t"))
        assert decision.scorecard_maturity == "cold"

    def test_scorecard_com_poucas_observacoes_e_warming(self):
        router = AdaptiveModelRouter(
            [_candidate()], [_scorecard(observations=2)]
        )
        decision = router.route(ModelRoutingInput(task_type="t"))
        assert decision.scorecard_maturity == "warming"
        assert decision.scorecard_observations == 2

    def test_scorecard_acima_do_limiar_e_mature(self):
        router = AdaptiveModelRouter(
            [_candidate()], [_scorecard(observations=9)]
        )
        decision = router.route(ModelRoutingInput(task_type="t"))
        assert decision.scorecard_maturity == "mature"

    def test_task_type_errado_nao_empresta_maturidade(self):
        """Scorecard de outro task_type nao conta -- maturity e por recorte."""
        router = AdaptiveModelRouter(
            [_candidate()], [_scorecard(task_type="outro", observations=9)]
        )
        decision = router.route(ModelRoutingInput(task_type="t"))
        assert decision.scorecard_maturity == "absent"


class TestRouteHealth:
    def test_axes_no_vocabulario_fechado(self):
        router = AdaptiveModelRouter([_candidate()], [_scorecard(observations=9)])
        health = router.route_health(ModelRoutingInput(task_type="t"))
        for axis, estado in health["axes"].items():
            assert estado in {"ready", "partial", "degraded", "unresolved"}, axis

    def test_sem_candidatos_compatíveis_health_e_degraded(self):
        router = AdaptiveModelRouter()
        health = router.route_health(ModelRoutingInput(task_type="t"))
        assert health["axes"]["candidate_coverage"] == "degraded"
        assert health["status"] == "degraded"

    def test_provider_availability_sempre_unresolved_offline(self):
        """O core e offline: disponibilidade de provider nao se mede local."""
        router = AdaptiveModelRouter([_candidate()], [_scorecard(observations=9)])
        health = router.route_health(ModelRoutingInput(task_type="t"))
        assert health["axes"]["provider_availability"] == "unresolved"

    def test_fallback_axis(self):
        router = AdaptiveModelRouter(
            [_candidate(model="m1"), _candidate(model="m2", provider="p2")],
            [_scorecard(observations=9)],
        )
        health = router.route_health(ModelRoutingInput(task_type="t"))
        assert health["axes"]["fallback_availability"] == "ready"
        solo = AdaptiveModelRouter([_candidate()]).route_health(
            ModelRoutingInput(task_type="t")
        )
        assert solo["axes"]["fallback_availability"] == "degraded"


class TestPromocaoNaoVemDeScore:
    def test_score_alto_nao_promove_sem_autoridade_e_evidencia(self):
        router = AdaptiveModelRouter(
            [_candidate()], [_scorecard(observations=99, quality=0.99)]
        )
        decision = router.route(
            ModelRoutingInput(task_type="t"), mode=ModelRouteMode.ACTIVE
        )
        assert not decision.applied
        assert "authority" in decision.reason


class TestDoctorAgentic:
    def test_scorecard_maturity_e_eixo_do_doctor(self, tmp_path):
        resultado = agentic_doctor(str(tmp_path))
        assert "scorecard_maturity" in resultado["checks"]
        # Sem scorecard persistido o eixo nao resolve -- e entra em
        # `unresolved` em vez de fingir prontidao.
        assert resultado["checks"]["scorecard_maturity"] is False
        assert "scorecard_maturity" in resultado["unresolved"]
