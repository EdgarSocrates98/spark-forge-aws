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

`TestTodaAreaAlcancaUmCoordenador` fecha o furo do outro lado, e ele custou
CINCO areas. `tests/test_agent_coverage.py::TestEveryRuleAreaHasACoordinator`
ja exigia que toda area do catalogo aparecesse em `rule_areas` de algum
coordenador -- mas declarar nao e ROTEAR. `SF-BENCH`, `SF-EMRS`, `SF-ENV`,
`SF-FVAL` e `SF-UI` estavam todas declaradas e nenhuma casava rota nenhuma: 26
regras cujo case voltava de `next_step` com `recommended_agent: None`. O caso
mais caro era `SF-EMRS`, declarada por `emr-infra-reviewer` desde a Fase 5d,
com a AGENT-007 casando `findings_area: SF-EMR` por igualdade exata.

Declaracao sem rota e o mesmo defeito que `requires_facts` sobre kind sem
extrator, e a resposta e a mesma: um invariante que reprova na origem, para que
a proxima area nao nasca orfa em silencio.
"""
import re
from pathlib import Path

import pytest
import yaml

from sparkforge.case.playbook import build_playbook
from sparkforge.case.router import next_step
from sparkforge.case.store import new_case, set_phase
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "rules" / "catalog" / "routing.yaml"
AGENTS = ROOT / "agents"


def _areas() -> list[str]:
    """As areas do catalogo, derivadas dos ids -- `rule["area"]` nao existe.

    `load_catalog` propaga `catalog_version` e `_source_file`, nunca o `area:` do
    cabecalho do YAML. Mesmo recorte de `tests/test_agent_coverage.py`.
    """
    return sorted({rule["id"].rsplit("-", 1)[0] for rule in load_catalog()})


def _primeira_regra_da_area(area: str) -> str:
    for rule in load_catalog():
        if rule["id"].rsplit("-", 1)[0] == area:
            return rule["id"]
    raise AssertionError(area)


def _rule_areas_declaradas() -> dict[str, set[str]]:
    declarado: dict[str, set[str]] = {}
    for path in sorted(AGENTS.glob("*.md")):
        block = path.read_text(encoding="utf-8").split("---", 2)[1]
        front = yaml.safe_load(block) or {}
        declarado[path.stem] = set(front.get("rule_areas") or [])
    return declarado


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


class TestTodaAreaAlcancaUmCoordenador:
    """O invariante derivado do D-6a-45, e ele mede `next_step`, nao o YAML.

    A pergunta e a do operador: "tenho achados desta area e nada mais -- quem
    investiga?". Ler o YAML responderia "ha uma rota escrita"; so chamar
    `next_step` responde "a rota casa e o nome sai no retorno".
    """

    @pytest.mark.parametrize("area", _areas())
    def test_uma_area_sozinha_devolve_coordenador(self, area):
        step = next_step(_case(), [_primeira_regra_da_area(area)])
        assert step["recommended_agent"], (
            f"{area} nao alcanca rota AGENT-* nenhuma: um case so com achados desta "
            f"area volta sem coordenador, e quem esta no playbook fica sem direcao. "
            f"Acrescente a area a uma rota existente ou escreva uma nova em "
            f"rules/catalog/routing.yaml, e diga na rota qual e a precedencia."
        )
        assert step["recommended_agent_reason"].startswith("AGENT-")

    @pytest.mark.parametrize("area", _areas())
    def test_o_coordenador_roteado_declara_a_area(self, area):
        """Rota e declaracao precisam concordar, ou uma das duas mente.

        Rotear para um agente que nao declara a area em `rule_areas` manda o
        case para quem nao disse saber investiga-la; declarar sem rotear e o
        defeito que este arquivo acabou de fechar. As duas metades juntas sao o
        que faz "quem investiga esta area" ter uma resposta so.
        """
        step = next_step(_case(), [_primeira_regra_da_area(area)])
        agente = step["recommended_agent"]
        declarado = _rule_areas_declaradas()
        assert area in declarado[agente], (
            f"{area} e roteada para {agente}, que nao a declara em `rule_areas`. "
            f"Declara: {sorted(declarado[agente])}."
        )

    def test_nenhuma_area_do_catalogo_fica_de_fora_da_medicao(self):
        """A parametrizacao vem do catalogo, e nao de uma lista escrita aqui.

        Area nova ganha caso de teste sozinha -- que e a unica forma de o
        invariante nao envelhecer junto com o catalogo.
        """
        assert len(_areas()) == len({rule["id"].rsplit("-", 1)[0] for rule in load_catalog()})
        for area in _areas():
            assert re.fullmatch(r"SF-[A-Z]+", area), area
