# tests/test_agent_coverage.py
"""Cobertura de capacidade por coordenador, como invariante.

21 das 29 tools MCP nao eram citadas em agente nenhum nem em skill nenhuma
quando esta fase abriu. A causa nao foi descuido pontual: cada fase alargou a
superficie do toolkit sem alargar a orientacao, e NADA reprovava. Este arquivo
e o que reprova.

E a versao de orientacao do `pyspark.unresolved`: capacidade que existe e nao e
alcancavel nao e capacidade, e a diferenca entre "nao ha o que usar ali" e
"ninguem documentou" tem que aparecer.
"""
import re
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters.tools import TOOLS
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
EXECUTORS = AGENTS / "executors"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path.name} sem frontmatter"
    block = text.split("---", 2)[1]
    return yaml.safe_load(block) or {}


def coordinators() -> list[Path]:
    return sorted(p for p in AGENTS.glob("*.md"))


def executors() -> list[Path]:
    return sorted(p for p in EXECUTORS.glob("*.md"))


def _corpus_of(path: Path) -> str:
    """Texto do coordenador MAIS o das skills e executores que ele declara.

    Alcancavel A PARTIR de um coordenador, nao apenas escrito nele: e assim que
    um agente real chega a capacidade -- lendo o coordenador e seguindo o que
    ele manda abrir.
    """
    front = _frontmatter(path)
    text = path.read_text(encoding="utf-8")
    for skill in front.get("skills") or []:
        skill_file = ROOT / "skills" / skill / "SKILL.md"
        if skill_file.is_file():
            text += skill_file.read_text(encoding="utf-8")
    for executor in front.get("executors") or []:
        executor_file = EXECUTORS / f"{executor}.md"
        if executor_file.is_file():
            text += executor_file.read_text(encoding="utf-8")
    return text


class TestEveryToolIsReachable:
    def test_no_tool_is_orphan(self):
        """Falha listando as orfas -- mensagem acionavel, nao contagem."""
        reachable = "".join(_corpus_of(p) for p in coordinators())
        orphans = sorted(name for name in TOOLS if name not in reachable)
        assert not orphans, (
            f"{len(orphans)} de {len(TOOLS)} tools nao sao alcancaveis a partir de "
            f"nenhum coordenador: {orphans}. Cite a tool no coordenador, numa skill "
            f"que ele declare, ou num executor que ele despache."
        )


class TestEveryRuleAreaHasACoordinator:
    def test_no_area_is_orphan(self):
        areas = sorted({r["id"].rsplit("-", 1)[0] for r in load_catalog()})
        declared: set[str] = set()
        for path in coordinators():
            declared |= set(_frontmatter(path).get("rule_areas") or [])
        missing = sorted(set(areas) - declared)
        assert not missing, (
            f"areas de regra sem coordenador: {missing}. Toda area precisa de alguem "
            f"que saiba quando investiga-la."
        )

    def test_every_declared_area_exists_in_the_catalog(self):
        """Area declarada que nao existe e ponteiro para o nada."""
        areas = {r["id"].rsplit("-", 1)[0] for r in load_catalog()}
        for path in coordinators():
            for area in _frontmatter(path).get("rule_areas") or []:
                assert area in areas, f"{path.name} declara {area}, que nao existe"


class TestCoordinatorExecutorWiring:
    def test_every_declared_executor_exists(self):
        available = {p.stem for p in executors()}
        for path in coordinators():
            for executor in _frontmatter(path).get("executors") or []:
                assert executor in available, f"{path.name} declara {executor}, ausente"

    def test_every_executor_is_declared_by_someone(self):
        """Executor que ninguem despacha e codigo morto com cara de capacidade."""
        declared: set[str] = set()
        for path in coordinators():
            declared |= set(_frontmatter(path).get("executors") or [])
        orphans = sorted({p.stem for p in executors()} - declared)
        assert not orphans, f"executores que nenhum coordenador despacha: {orphans}"

    # ids como lista pre-computada, nao callable: com a lista de executores
    # vazia (ainda sem `agents/executors/`), um `ids=lambda p: p.stem` faz o
    # pytest 8.x invocar a funcao sobre o sentinela interno NOTSET durante a
    # coleta e abortar a sessao inteira (todos os arquivos, nao so este). Uma
    # lista pronta evita a chamada e deixa so este teste vermelho, como e o
    # ponto da task.
    @pytest.mark.parametrize("path", executors(), ids=[p.stem for p in executors()])
    def test_every_executor_declares_its_negative_boundary(self, path):
        """A secao 4.2 da Fase 0 diz que a fronteira NEGATIVA e o mecanismo que
        garante o determinismo. Executor sem ela vira coordenador disfarcado."""
        text = path.read_text(encoding="utf-8")
        assert "## Não faz" in text, f"{path.name} sem secao `## Não faz`"


class TestHandoffContract:
    """Executor isolado nao e time; e cinco agentes repetindo trabalho.

    O que faz os executores trabalharem EM CONJUNTO nao e a ordem em que o
    coordenador os despacha -- e o estado que cada um deixa para o seguinte.
    Sem contrato de entrega, cada executor reconstroi o que o anterior ja sabia,
    e a decomposicao vira cinco investigacoes paralelas com o mesmo custo de uma
    sozinha, so que divergindo entre si.

    O estado compartilhado e `.sparkforge/case.yaml`: nenhum executor guarda
    contexto proprio, pela mesma razao que a Fase 0 pos o roteamento em dado --
    estado que sobrevive a troca de sessao, de modelo e de ferramenta.
    """

    # Mesmo motivo do guard acima: ids pre-computada, nao callable.
    @pytest.mark.parametrize("path", executors(), ids=[p.stem for p in executors()])
    def test_every_executor_declares_what_it_hands_over(self, path):
        text = path.read_text(encoding="utf-8")
        assert "## Entrega" in text, (
            f"{path.name} sem secao `## Entrega`. Sem dizer o que escreve no case, "
            f"o executor seguinte nao sabe o que pode assumir -- e reconstroi."
        )

    # Mesmo motivo do guard acima: ids pre-computada, nao callable.
    @pytest.mark.parametrize("path", executors(), ids=[p.stem for p in executors()])
    def test_every_executor_declares_what_it_expects(self, path):
        """A outra ponta do contrato: o que ele PRESSUPOE ja no case.

        `sf-inventory` e o unico que pode comecar do zero. Os demais dependem do
        anterior, e declarar isso e o que permite o coordenador saber que pulou
        um passo em vez de descobrir por resultado estranho.
        """
        text = path.read_text(encoding="utf-8")
        assert "## Pressupõe" in text, f"{path.name} sem secao `## Pressupõe`"

    def test_the_chain_closes(self):
        """O que um entrega, o seguinte pressupoe -- nenhum elo solto.

        Compara as chaves de case declaradas por cada executor na ordem do loop
        de fase. Uma chave pressuposta que ninguem entrega e um elo quebrado: o
        executor vai procurar no case algo que nunca foi escrito.
        """
        order = ["sf-inventory", "sf-extractor", "sf-judge", "sf-verifier", "sf-synthesizer"]
        delivered: set[str] = set()
        for name in order:
            text = (EXECUTORS / f"{name}.md").read_text(encoding="utf-8")
            expects = set(re.findall(r"`case\.([a-z_.]+)`", _section(text, "Pressupõe")))
            missing = expects - delivered
            assert not missing, (
                f"{name} pressupoe {sorted(missing)}, que nenhum executor anterior "
                f"entrega. Elo quebrado na cadeia."
            )
            delivered |= set(re.findall(r"`case\.([a-z_.]+)`", _section(text, "Entrega")))


class TestOTerceiroDegrauAlcancaAAssinatura:
    """`TestEveryToolIsReachable` le o corpus do COORDENADOR -- ele mais as
    skills e executores que ele declara --, entao uma tool citada so no executor
    ja passa. Foi assim que `report sign` ficou alcancavel pelo agente e
    inalcancavel pela skill: `agents/executors/sf-synthesizer.md` a invoca,
    `AGENT_PROTOCOL.md` a descreve, e `grep -rl "report sign" skills/` saia
    vazio.

    A escada de degradacao tem tres degraus -- tools MCP, CLI, e o Markdown que
    um agente sem Python le. Skill e o terceiro, e e o unico que sobrevive a
    queda dos outros dois: quem segue uma skill de ponta a ponta chega ao
    relatorio, e ate aqui nunca era mandado assina-lo. Assinatura nao e
    obrigatoria (`strict_gates` guarda a transicao de fase, nao a emissao do
    relatorio) -- ser ALCANCAVEL por este degrau e que e.

    O teste cobra o DEGRAU, nao um arquivo: qualquer skill serve, porque a
    pergunta e "um agente que so le skills chega la?".
    """

    CAPABILITIES = ("report sign", "report verify")

    def _skills_corpus(self) -> str:
        return "".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "skills").glob("*/SKILL.md"))
        )

    def test_a_assinatura_e_alcancavel_so_pelas_skills(self):
        corpus = self._skills_corpus()
        missing = [name for name in self.CAPABILITIES if name not in corpus]
        assert not missing, (
            f"nenhuma skill cita {missing}. A capacidade existe e o terceiro "
            f"degrau da escada nao chega nela: quem seguir so o Markdown escreve "
            f"o relatorio e nunca e mandado assinar nem conferir."
        )

    def test_o_corpus_nao_e_vazio(self):
        """Se o glob parar de achar SKILL.md, o teste acima vira verde sobre
        nada -- a mesma armadilha do invariante derivado por AST."""
        corpus = self._skills_corpus()

        assert "sparkforge-diagnose" in corpus, len(corpus)
        assert len(list((ROOT / "skills").glob("*/SKILL.md"))) >= 20


def _section(text: str, title: str) -> str:
    """Corpo de uma secao `## <title>` ate a proxima `##` ou o fim."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


class TestEMRonEKSTemDespachoCompleto:
    """As TRES metades do despacho de uma area, cobradas juntas para `SF-EMRK`.

    Os invariantes genericos deste arquivo e do `test_router_agents.py` ja
    cobrem cada metade em separado, e foi assim que `SF-EMRS` conseguiu ficar
    declarada num coordenador e sem rota nenhuma por uma fase inteira: cada
    teste passava sozinho porque cada um olhava para um lado so.

    Aqui as tres sao a mesma assercao, sobre a area que a fase de EMR on EKS
    acrescentou:

    1. `SF-EMRK` casa uma rota `AGENT-*` em `routing.yaml`;
    2. a rota aponta para um coordenador que DECLARA a area em `rule_areas` --
       rota para agente que nao conhece a area e ponteiro para o nada;
    3. as duas tools de `emr-containers` sao alcancaveis a partir de algum
       coordenador, pelo mesmo corpus de `TestEveryToolIsReachable`.
    """

    AREA = "SF-EMRK"
    TOOLS_DA_AREA = ("sparkforge_analyze_emr_eks", "sparkforge_collect_emr_eks")

    def _routing(self) -> dict:
        path = ROOT / "rules" / "catalog" / "routing.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _rotas_da_area(self) -> list[dict]:
        rotas = []
        for rule in self._routing()["rules"]:
            if not rule.get("recommended_agent"):
                continue
            grupo = rule.get("when") or {}
            condicoes = (grupo.get("any") or []) + (grupo.get("all") or [])
            if any(c.get("findings_area") == self.AREA for c in condicoes):
                rotas.append(rule)
        return rotas

    def test_a_area_existe_no_catalogo(self):
        """Guarda contra os tres testes abaixo passarem sobre uma area que
        deixou de existir -- verde sobre nada e o defeito que este arquivo
        inteiro persegue."""
        areas = {r["id"].rsplit("-", 1)[0] for r in load_catalog()}
        assert self.AREA in areas, f"{self.AREA} nao esta no catalogo"

    def test_a_area_casa_uma_rota(self):
        rotas = self._rotas_da_area()
        assert rotas, (
            f"{self.AREA} nao aparece em condicao `findings_area` de rota nenhuma em "
            f"routing.yaml: um case so com achados desta area volta de `next_step` "
            f"com `recommended_agent: None`."
        )

    def test_o_agente_da_rota_declara_a_area(self):
        declarado = {p.stem: set(_frontmatter(p).get("rule_areas") or []) for p in coordinators()}
        for rota in self._rotas_da_area():
            agente = rota["recommended_agent"]
            assert agente in declarado, f"{rota['id']} aponta para {agente}, inexistente"
            assert self.AREA in declarado[agente], (
                f"{rota['id']} roteia {self.AREA} para {agente}, que nao a declara em "
                f"`rule_areas`: despacho sem declaracao manda o case para quem nao "
                f"sabe que a area existe."
            )

    def test_as_duas_tools_de_emr_containers_sao_alcancaveis(self):
        reachable = "".join(_corpus_of(p) for p in coordinators())
        orphans = [name for name in self.TOOLS_DA_AREA if name not in reachable]
        assert not orphans, (
            f"{orphans} nao sao alcancaveis a partir de nenhum coordenador. Cite-as no "
            f"coordenador, numa skill que ele declare, ou num executor que ele despache."
        )
