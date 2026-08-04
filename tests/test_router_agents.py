# tests/test_router_agents.py
"""Escolher coordenador e consulta, nao julgamento.

Manter os 3 agentes antigos e acrescentar 3 novos cria dois vocabularios --
risco levantado e aceito ao decidir F4-D2. A tabela e o que o neutraliza:
a mesma coisa que `next_step` fez com a escolha de skill.

`TestAgentRoutes` cobre so o metadado do YAML -- e o que deixou as rotas
`AGENT-*` serem codigo morto por uma fase inteira: nenhum teste chamava
`next_step` de verdade para ver se `recommended_agent` saia no retorno.
`TestAgentRoutePropagation` fecha esse furo chamando `next_step` como um
agente chamaria.
"""
from pathlib import Path

import yaml

from sparkforge.case.playbook import build_playbook
from sparkforge.case.router import next_step
from sparkforge.case.store import new_case, set_phase

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "rules" / "catalog" / "routing.yaml"
AGENTS = ROOT / "agents"

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def _case(phase="diagnosis", **over):
    base = set_phase(new_case("c", "2026-07-29T00:00:00Z", RUNTIME), phase)
    for key, value in over.items():
        base[key] = value
    return base


def _routing() -> dict:
    return yaml.safe_load(ROUTING.read_text(encoding="utf-8"))


def _agent_routes() -> list[dict]:
    return [r for r in _routing()["rules"] if r.get("recommended_agent")]


class TestAgentRoutes:
    def test_there_is_at_least_one_route_per_coordinator(self):
        coordinators = {p.stem for p in AGENTS.glob("*.md")}
        routed = {r["recommended_agent"] for r in _agent_routes()}
        missing = sorted(coordinators - routed)
        assert not missing, f"coordenadores sem rota: {missing}"

    def test_every_routed_agent_exists(self):
        coordinators = {p.stem for p in AGENTS.glob("*.md")}
        for route in _agent_routes():
            assert route["recommended_agent"] in coordinators, route["id"]

    def test_agent_routes_have_id_and_reason(self):
        for route in _agent_routes():
            assert route["id"].startswith("AGENT-"), route
            assert route.get("reason"), route["id"]

    def test_agent_route_ids_are_unique(self):
        ids = [r["id"] for r in _agent_routes()]
        assert len(ids) == len(set(ids))


class TestAgentRoutePropagation:
    """O defeito de verdade: `next_step` nunca devolvia `recommended_agent`,
    mesmo com uma rota AGENT-* casando em cheio. Estes testes chamam
    `next_step`, nao o YAML cru -- e o unico jeito de morder essa regressao.
    """

    def test_glue_finding_routes_to_glue_infra_reviewer(self):
        step = next_step(_case(), ["SF-GLUE-002"])
        assert step["recommended_agent"] == "glue-infra-reviewer"
        assert step["recommended_agent_reason"].startswith("AGENT-002")

    def test_no_finding_yields_no_agent_without_breaking(self):
        step = next_step(_case(), [])
        assert step["recommended_agent"] is None
        assert step["recommended_agent_reason"] is None
        # a ausencia de rota de agente nao e erro: o resto do payload continua util.
        assert step["recommended_skill"]

    def test_recommended_skill_is_unaffected_by_the_agent_route(self):
        """Regressao: resolver `recommended_agent` ao lado nao pode mudar qual
        skill `next_step` recomenda -- e a garantia que o teste antigo
        (`test_case_router.py`) ja cobre por rota, mas aqui de novo no mesmo
        caso do teste acima, com achado de SF-GLUE, para deixar explicito que
        as duas rotas (skill e agente) convivem sem se pisar."""
        step = next_step(_case(), ["SF-GLUE-002"])
        assert step["recommended_skill"] == "sparkforge-diagnose"
        assert "Nenhuma regra" in step["reason"]

    def test_alternatives_never_contain_an_agent_route(self):
        """`alternatives` so projeta `recommended_skill`; uma rota AGENT-* ali
        dentro reintroduziria o `KeyError` que a Task 4 corrigiu filtrando as
        rotas de agente para fora da lista de skill inteira."""
        step = next_step(_case(), ["SF-PY-004", "SF-GLUE-002", "SF-PQ-002"])
        for alt in step["alternatives"]:
            assert "recommended_agent" not in alt

    def test_playbook_carries_next_step_with_the_resolved_agent(self):
        """A spec exige o playbook preenchido com o `next_step` do case (secao
        4.5) -- sem isso, quem esta no `playbook` (sempre em Codex e Copilot CI,
        e nas outras tres quando o despacho esta desligado) fica sem a mesma
        direcao que quem despacha tem ao escolher o perfil."""
        playbook = build_playbook(
            "glue-infra-reviewer", _case(), finding_ids=["SF-GLUE-002"]
        )
        assert playbook["next_step"]["recommended_agent"] == "glue-infra-reviewer"
