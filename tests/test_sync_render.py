"""O renderizador por plataforma de `scripts/sync_skills.py`.

Fundamento medido: `knowledge/devin/agents-and-subagents.md` (retrieved
2026-08-04), vetos `V-DV-2`, `V-DV-3` e `V-DV-8`. Spec: D-1, D-2 e D-3 de
`docs/superpowers/specs/2026-08-04-sparkforge-devin-subagentes-design.md`.
"""
from pathlib import Path

import pytest
import yaml

from scripts import sync_skills
from scripts.sync_skills import render_agent

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
EXECUTORS = AGENTS / "executors"
PERFIS = tuple(sorted(AGENTS.glob("*.md")) + sorted(EXECUTORS.glob("*.md")))


SKILL_SINTETICA = """---
name: skill-sintetica
description: Use quando.
---

Corpo da skill.
"""


SOURCE = """---
name: emr-infra-reviewer
description: Use quando o Spark roda em EMR on EC2.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - review-emr-cluster
rule_areas: [SF-EMR]
executors: [sf-inventory]
---

Corpo do perfil.
"""


# `tools:` em forma de bloco. Nenhum dos treze perfis reais usa esta forma hoje
# (medido), mas um regex ingenuo que apagasse so a linha `tools:` deixaria
# `  - Read` orfao e quebraria o YAML do espelho no dia em que alguem escrevesse
# assim. O teste fixa a forma antes de ela existir.
SOURCE_TOOLS_EM_BLOCO = """---
name: perfil-em-bloco
description: Frontmatter com tools em forma de lista.
tools:
  - Read
  - Grep
  - Bash
skills:
  - review-emr-cluster
rule_areas: [SF-EMR]
---

Corpo do perfil.
"""


def test_claude_recebe_o_arquivo_inalterado():
    assert render_agent(SOURCE, platform="claude") == SOURCE


def test_github_recebe_o_arquivo_inalterado():
    assert render_agent(SOURCE, platform="github") == SOURCE


def test_devin_perde_o_campo_tools():
    """O mapeamento de valores de `tools:` NAO esta documentado (V-DV-8 da
    pesquisa). Chute em campo de permissao concede ou nega errado, e nos dois
    sentidos o erro e caro. Omitido, o subagente herda o que o harness da."""
    out = render_agent(SOURCE, platform="devin")
    assert "tools:" not in out
    assert "name: emr-infra-reviewer" in out
    assert "rule_areas: [SF-EMR]" in out
    assert "Corpo do perfil." in out


def test_devin_nunca_ganha_model():
    """O default resolve por roteador no spawn e o admin da org sobrescreve.
    Escrever `model:` seria fingir controle sobre o que o harness decide."""
    assert "model:" not in render_agent(SOURCE, platform="devin")


def test_render_e_idempotente():
    once = render_agent(SOURCE, platform="devin")
    assert render_agent(once, platform="devin") == once


class TestFormaDoCampo:
    def test_devin_leva_as_continuacoes_de_tools_em_bloco(self):
        """Regex ingenuo deixaria `  - Read` orfao, e o frontmatter do espelho
        deixaria de ser YAML valido."""
        out = render_agent(SOURCE_TOOLS_EM_BLOCO, platform="devin")
        assert "tools:" not in out
        assert "  - Read" not in out
        assert "  - Grep" not in out
        assert "  - Bash" not in out

    def test_bloco_de_tools_nao_leva_junto_a_lista_de_skills(self):
        """`skills:` vem logo depois e tambem e lista indentada. Se a remocao
        nao parar na proxima chave de topo, ela come a chave seguinte inteira."""
        out = render_agent(SOURCE_TOOLS_EM_BLOCO, platform="devin")
        assert "skills:\n  - review-emr-cluster\n" in out
        assert "rule_areas: [SF-EMR]" in out

    def test_forma_em_bloco_tambem_e_idempotente(self):
        once = render_agent(SOURCE_TOOLS_EM_BLOCO, platform="devin")
        assert render_agent(once, platform="devin") == once


class TestCamposQueSaoNossos:
    """`skills:`, `rule_areas:` e `executors:` sao deste repositorio. O Devin
    ignora campo que nao conhece; removê-los perderia a informacao que os
    invariantes das fases anteriores usam."""

    def test_skills_rule_areas_e_executors_sobrevivem(self):
        out = render_agent(SOURCE, platform="devin")
        assert "skills:\n  - review-emr-cluster\n" in out
        assert "rule_areas: [SF-EMR]" in out
        assert "executors: [sf-inventory]" in out


class TestPerfisReais:
    """Os treze arquivos que o espelho do Devin vai receber na Task 2."""

    def test_o_corpus_tem_treze_perfis(self):
        assert len(PERFIS) >= 13

    def test_passthrough_devolve_byte_a_byte(self):
        for perfil in PERFIS:
            texto = perfil.read_text(encoding="utf-8")
            for plataforma in ("claude", "github"):
                assert render_agent(texto, platform=plataforma) == texto, perfil.name

    def test_devin_perde_tools_em_todos(self):
        for perfil in PERFIS:
            out = render_agent(perfil.read_text(encoding="utf-8"), platform="devin")
            assert "tools:" not in out, perfil.name

    def test_devin_nao_ganha_model_em_nenhum(self):
        for perfil in PERFIS:
            out = render_agent(perfil.read_text(encoding="utf-8"), platform="devin")
            assert "model:" not in out, perfil.name

    def test_devin_so_perde_a_linha_de_tools(self):
        """A remocao e cirurgica: o resto do arquivo sai igual, linha a linha.
        Round-trip de YAML reordenaria chaves e produziria diff onde nao houve
        mudanca -- e o gate da Task 2 viraria ruido."""
        for perfil in PERFIS:
            texto = perfil.read_text(encoding="utf-8")
            out = render_agent(texto, platform="devin")
            antes = texto.splitlines(keepends=True)
            removidas = [linha for linha in antes if linha not in out.splitlines(keepends=True)]
            assert out == "".join(
                linha for linha in antes if not linha.startswith("tools:")
            ), (perfil.name, removidas)

    def test_o_corpo_sobrevive_inteiro(self):
        for perfil in PERFIS:
            texto = perfil.read_text(encoding="utf-8")
            corpo = texto.split("\n---\n", 1)[1]
            assert corpo in render_agent(texto, platform="devin"), perfil.name

    def test_render_dos_perfis_reais_e_idempotente(self):
        for perfil in PERFIS:
            once = render_agent(perfil.read_text(encoding="utf-8"), platform="devin")
            assert render_agent(once, platform="devin") == once, perfil.name


class TestBordas:
    def test_plataforma_desconhecida_falha_alto(self):
        """Erro de digitacao em nome de plataforma nao pode virar passthrough
        silencioso: o espelho sairia com `tools:` e ninguem saberia."""
        with pytest.raises(ValueError):
            render_agent(SOURCE, platform="cursor")

    def test_texto_sem_frontmatter_sai_inalterado(self):
        texto = "Sem frontmatter nenhum.\ntools: Read\n"
        assert render_agent(texto, platform="devin") == texto

    def test_tools_no_corpo_nao_e_tocado(self):
        """Fora do frontmatter, `tools:` e prosa. Remover ali seria editar o
        metodo do perfil."""
        texto = SOURCE + "\nA secao abaixo cita tools: Read no corpo.\n"
        out = render_agent(texto, platform="devin")
        assert "A secao abaixo cita tools: Read no corpo." in out

    def test_fim_de_linha_e_preservado(self):
        """O espelho e comparado byte a byte pelo gate; normalizar CRLF para LF
        produziria DIVERGENTE em toda regeneracao numa arvore com autocrlf."""
        crlf = SOURCE.replace("\n", "\r\n")
        out = render_agent(crlf, platform="devin")
        assert "\r\n" in out
        assert "\n" not in out.replace("\r\n", "")
        assert "tools:" not in out


# ---------------------------------------------------------------------------
# Task 4: skills que despacham
# ---------------------------------------------------------------------------
# Fundamento medido: `knowledge/devin/agents-and-subagents.md` secao 8 --
# `.agents/skills/<name>/SKILL.md` e caminho de descoberta NATIVO do Devin, e o
# frontmatter de skill aceita `subagent` (bool, default `false`) e `agent`
# (string, default nenhum). Spec: D-5 e D-6.

SKILLS = ROOT / "skills"
SKILL_DIRS = tuple(sorted(p for p in SKILLS.iterdir() if p.is_dir()))

# A saida literal do Step 1, medida sobre `agents/*.md` antes de qualquer
# decisao. Esta constante NAO e a fonte -- a fonte e o `skills:` de cada perfil,
# e `coordinators_by_skill()` a le de la. Ela existe para que uma mudanca na
# relacao apareca como diff aqui, em vez de mudar `agent:` no espelho em
# silencio.
RELACAO_MEDIDA = {
    "analyze-batch-loop": (
        "glue-incremental-performance-architect",
        "pyspark-code-reviewer",
    ),
    "analyze-library-call-graph": (
        "data-quality-reviewer",
        "glue-incremental-performance-architect",
        "pyspark-code-reviewer",
    ),
    "analyze-spark-plan": (
        "glue-incremental-performance-architect",
        "pyspark-code-reviewer",
        "spark-performance-architect",
    ),
    "analyze-spark-ui": (
        "emr-infra-reviewer",
        "glue-incremental-performance-architect",
        "spark-performance-architect",
    ),
    "benchmark-pyspark-job": (
        "athena-query-optimizer",
        "emr-infra-reviewer",
        "glue-incremental-performance-architect",
        "iceberg-performance-engineer",
        "spark-performance-architect",
    ),
    "design-incremental-processing": ("glue-incremental-performance-architect",),
    "diagnose-data-skew": (
        "glue-incremental-performance-architect",
        "spark-performance-architect",
    ),
    "diagnose-oom": ("glue-incremental-performance-architect",),
    "glue-incremental-performance-architect": ("glue-incremental-performance-architect",),
    "optimize-iceberg-table": (
        "athena-query-optimizer",
        "glue-incremental-performance-architect",
        "iceberg-performance-engineer",
        "spark-performance-architect",
    ),
    "optimize-latest-per-key": ("glue-incremental-performance-architect",),
    "optimize-parquet-layout": (
        "athena-query-optimizer",
        "glue-incremental-performance-architect",
        "iceberg-performance-engineer",
        "sf-parquet-specialist",
        "spark-performance-architect",
    ),
    "optimize-pyspark-code": (
        "glue-incremental-performance-architect",
        "pyspark-code-reviewer",
        "spark-performance-architect",
    ),
    "optimize-variable-volume-job": (
        "glue-incremental-performance-architect",
        "glue-infra-reviewer",
    ),
    "review-data-validation": (
        "data-quality-reviewer",
        "sf-evidence-verifier",
        "sf-kinesis-specialist",
        "sf-schema-registry-specialist",
    ),
    "review-emr-cluster": ("emr-infra-reviewer",),
    "review-glue-terraform": (
        "glue-incremental-performance-architect",
        "glue-infra-reviewer",
    ),
    "review-pyspark-pr": (
        "data-quality-reviewer",
        "pyspark-code-reviewer",
        "spark-performance-architect",
    ),
    "sparkforge-diagnose": (
        "glue-incremental-performance-architect",
        "spark-performance-architect",
    ),
    "tune-glue-job": (
        "glue-incremental-performance-architect",
        "glue-infra-reviewer",
        "spark-performance-architect",
    ),
    "design-data-architecture": (
        "sf-cost-reviewer",
        "sf-data-architect",
        "sf-kinesis-specialist",
        "sf-lake-formation-specialist",
        "sf-lineage-specialist",
        "sf-schema-registry-specialist",
        "sf-security-reviewer",
    ),
    "design-airflow-pipelines": ("sf-airflow-specialist",),
    "design-agent-systems": (
        "sf-agent-builder",
        "sf-agent-evaluation-specialist",
        "sf-memory-engineer",
    ),
    "optimize-iceberg-tables": ("sf-iceberg-specialist",),
    "design-s3-data-lake": (
        "sf-lake-formation-specialist",
        "sf-s3-specialist",
        "sf-security-reviewer",
    ),
    "review-terraform-data-platform": (
        "sf-lake-formation-specialist",
        "sf-security-reviewer",
        "sf-terraform-specialist",
    ),
    "analyze-graph-data": ("sf-graph-specialist",),
    "design-neptune-graph": ("sf-neptune-specialist",),
    "design-dynamodb-model": ("sf-dynamodb-specialist",),
    "optimize-athena-queries": (
        "sf-athena-specialist",
        "sf-cost-reviewer",
    ),
    "analyze-analytics": (
        "sf-analytics-specialist",
        "sf-lineage-specialist",
    ),
    "analyze-functional-rules": (
        "sf-functional-rules-specialist",
        "sf-lineage-specialist",
        "sf-schema-registry-specialist",
    ),
    "agentic-orchestration": (
        "sf-agent-evaluation-specialist",
        "sf-context-engineer",
        "sf-evidence-verifier",
        "sf-memory-engineer",
        "sf-orchestrator",
    ),
    "token-efficient-agent": (
        "sf-agent-evaluation-specialist",
        "sf-context-engineer",
        "sf-cost-reviewer",
        "sf-memory-engineer",
        "sf-orchestrator",
        "sf-token-verifier",
    ),
    "tool-specialist-routing": (
        "sf-context-engineer",
        "sf-evidence-verifier",
        "sf-orchestrator",
        "sf-pyspark-specialist",
        "sf-runtime-specialist",
        "sf-storage-specialist",
    ),
    "design-lambda-serverless": ("sf-lambda-serverless-specialist",),
    "design-step-functions-orchestration": (
        "sf-kinesis-specialist",
        "sf-step-functions-specialist",
    ),
    "verify-agent-evidence": ("sf-evidence-verifier",),
    "engineer-agent-context": ("sf-context-engineer",),
    "engineer-agent-memory": ("sf-memory-engineer",),
}


def _bloco_do_frontmatter(text: str) -> str:
    assert text.startswith("---"), "SKILL.md sem cerca de abertura"
    return text[3 : text.index("\n---", 3)]


def _frontmatter(text: str) -> dict:
    """As chaves de topo do frontmatter, lidas linha a linha.

    **Medido, e e por isso que este leitor nao usa `yaml.safe_load`:** o
    frontmatter das skills reais nao e YAML estrito. Cinco das vinte
    descricoes citam comando com dois-pontos dentro de escalar simples
    (``rode `sparkforge analyze plan`: ele emite``), e `safe_load` levanta
    `ScannerError` nelas. E o mesmo motivo pelo qual `test_skill_content` tem o
    proprio `parse_frontmatter` de linha.

    Onde o YAML *importa* -- provar que a insercao nao quebrou a cerca -- os
    testes de borda usam `_yaml_estrito` sobre fonte sintetica, que e YAML
    valido de proposito.
    """
    campos: dict[str, str] = {}
    for linha in _bloco_do_frontmatter(text).splitlines():
        if linha[:1] in (" ", "\t") or ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        campos[chave.strip()] = valor.strip()
    return campos


def _yaml_estrito(text: str) -> dict:
    """O frontmatter como YAML de verdade.

    O renderizador nao faz round-trip de YAML de proposito; o teste faz, e e por
    isso que ele pega o modo de falha simetrico da insercao: campo posto na
    posicao errada quebra a cerca, e ai `safe_load` levanta ou devolve outra
    coisa em vez do dicionario esperado.
    """
    return yaml.safe_load(_bloco_do_frontmatter(text))


def _lista_de_topo(text: str, chave: str) -> list[str]:
    """Uma lista de bloco do frontmatter, sem passar pelo codigo sob teste.

    O invariante bidirecional perde o sentido se os dois lados sairem da mesma
    funcao: um bug em `_frontmatter_list` esconderia a quebra dos dois lados de
    uma vez.
    """
    valores: list[str] = []
    lendo = False
    for linha in _bloco_do_frontmatter(text).splitlines():
        if linha[:1] in (" ", "\t"):
            if lendo and linha.strip().startswith("- "):
                valores.append(linha.strip()[2:].strip())
            continue
        lendo = linha.strip() == f"{chave}:"
    return valores


class TestRelacaoDerivada:
    """D-5: `agent:` sai do `skills:` que cada coordenador ja declara."""

    def test_a_relacao_e_a_medida(self):
        assert sync_skills.coordinators_by_skill() == RELACAO_MEDIDA

    def test_a_constante_e_declarada_uma_vez_so(self):
        """`RELACAO_MEDIDA` nao pode ser remendada depois da declaracao.

        A expansao agentica acrescentou as skills novas por um
        `RELACAO_MEDIDA.update({...})` ~160 linhas abaixo da declaracao, e o
        resultado foi **12 chaves com valor morto** no literal de cima: quem
        editasse a entrada de `design-data-architecture` ali achava que tinha
        mudado o teste e nao tinha mudado nada -- o `update()` sobrescrevia.
        Numa constante cuja razao de existir e "a mudanca aparece como diff
        aqui", editar o lugar errado em silencio e o pior defeito possivel.

        O teste le o PROPRIO fonte por AST em vez de inspecionar o dicionario
        em memoria, porque depois que o modulo carrega os dois jeitos de montar
        a constante sao indistinguiveis -- e e exatamente a forma de montar que
        esta sob teste.
        """
        import ast

        modulo = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        atribuicoes = [
            no
            for no in ast.walk(modulo)
            if isinstance(no, ast.Assign)
            and any(
                isinstance(alvo, ast.Name) and alvo.id == "RELACAO_MEDIDA"
                for alvo in no.targets
            )
        ]
        assert len(atribuicoes) == 1, (
            f"RELACAO_MEDIDA atribuida {len(atribuicoes)} vezes; "
            f"a constante e uma declaracao so"
        )

        mutacoes = [
            no
            for no in ast.walk(modulo)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and isinstance(no.func.value, ast.Name)
            and no.func.value.id == "RELACAO_MEDIDA"
            and no.func.attr in {"update", "setdefault", "pop", "clear"}
        ]
        assert not mutacoes, (
            "RELACAO_MEDIDA mutada depois da declaracao por "
            f"{sorted({no.func.attr for no in mutacoes})}: acrescente a chave na "
            "declaracao, senao o valor de la vira letra morta"
        )

    def test_toda_skill_do_disco_esta_na_relacao(self):
        """Skill que nenhum coordenador declara nao teria de onde derivar
        `agent:`."""
        orfas = [p.name for p in SKILL_DIRS if p.name not in RELACAO_MEDIDA]
        assert not orfas, orfas

    def test_o_caso_ambiguo_existe_e_e_a_maioria(self):
        """Medido, e o numero e o que decide o desenho: 14 das 20 skills sao
        declaradas por MAIS DE UM coordenador. Nelas `agent:` nao tem resposta
        unica, e nenhuma regra deterministica a inventa sem mentir."""
        ambiguas = [s for s, c in RELACAO_MEDIDA.items() if len(c) > 1]
        assert len(ambiguas) >= 14
        assert len(RELACAO_MEDIDA) >= 20

    def test_agent_for_skill_cala_no_caso_ambiguo(self):
        for skill, coordenadores in RELACAO_MEDIDA.items():
            if len(coordenadores) > 1:
                assert sync_skills.agent_for_skill(skill) is None, skill

    def test_agent_for_skill_nomeia_o_unico_quando_ele_nao_orquestra(self):
        orquestradores = sync_skills.orchestrator_profiles()
        for skill, coordenadores in RELACAO_MEDIDA.items():
            if len(coordenadores) == 1 and coordenadores[0] not in orquestradores:
                assert sync_skills.agent_for_skill(skill) == coordenadores[0], skill

    def test_declarante_unico_que_orquestra_nao_vira_agent(self):
        """`diagnose-oom`, medida na revisao final de 2026-08-04.

        Ela era declarante unico **por omissao**: `spark-performance-architect`
        nao lista `diagnose-oom` no `skills:` dele, embora liste
        `diagnose-data-skew`, `analyze-spark-ui` e `tune-glue-job` -- toda a
        vizinhanca do mesmo diagnostico. E o perfil que sobrava era o
        orquestrador, cuja skill homonima este repositorio declara
        nao-despachavel exatamente por orquestrar via `next-step`.
        """
        assert RELACAO_MEDIDA["diagnose-oom"] == (
            "glue-incremental-performance-architect",
        )
        assert "diagnose-oom" not in _lista_de_topo(
            (AGENTS / "spark-performance-architect.md").read_text(encoding="utf-8"),
            "skills",
        )
        assert sync_skills.agent_for_skill("diagnose-oom") is None

    def test_o_conjunto_de_orquestradores_e_derivado_e_tem_um_elemento(self):
        """Derivado de `NON_DISPATCHABLE_SKILLS` cruzado com os perfis em disco --
        nao e lista mantida a mao. `sparkforge-diagnose` tambem nao despacha e
        NAO entra: nao existe perfil homonimo a ela."""
        assert sync_skills.orchestrator_profiles() == {
            "glue-incremental-performance-architect"
        }
        assert "sparkforge-diagnose" in sync_skills.NON_DISPATCHABLE_SKILLS
        assert not (AGENTS / "sparkforge-diagnose.md").exists()

    def test_a_ordem_alfabetica_seria_o_perfil_errado(self):
        """O contraexemplo que matou a alternativa "declara o primeiro em ordem
        deterministica": ordem alfabetica nao e criterio de competencia."""
        assert RELACAO_MEDIDA["review-pyspark-pr"][0] == "data-quality-reviewer"
        assert "pyspark-code-reviewer" in RELACAO_MEDIDA["review-pyspark-pr"]
        assert sync_skills.agent_for_skill("review-pyspark-pr") is None


class TestQuemDespacha:
    """D-6: despacha investigacao fechada; nao despacha quem dirige o loop ou
    precisa perguntar."""

    def test_a_particao_cobre_skills_exatamente(self):
        """Skill nova cai em qual lado? Em nenhum -- e e assim que se descobre
        que ninguem decidiu. O default silencioso publicaria a skill sem alguem
        ter perguntado se ela consegue trabalhar sem poder perguntar."""
        assert set(sync_skills.SKILL_DISPATCH_REASON) == {p.name for p in SKILL_DIRS}
        assert not (
            set(sync_skills.DISPATCHABLE_SKILLS)
            & set(sync_skills.NON_DISPATCHABLE_SKILLS)
        )

    def test_toda_decisao_tem_razao_escrita(self):
        vazias = [
            n for n, r in sync_skills.SKILL_DISPATCH_REASON.items() if not r.strip()
        ]
        assert not vazias, vazias

    def test_sparkforge_diagnose_nao_despacha(self):
        """Ela abre o case e roteia. Despachar jogaria o ciclo de vida do case
        para um contexto que NAO VOLTA -- o subagente nao herda o historico do
        pai, e a saida dele e texto livre que o pai resume (pesquisa, secao 6). E
        o case e justamente o que faz a investigacao atravessar sessoes."""
        assert "sparkforge-diagnose" not in sync_skills.DISPATCHABLE_SKILLS
        assert "case" in sync_skills.NON_DISPATCHABLE_SKILLS["sparkforge-diagnose"]
        texto = (SKILLS / "sparkforge-diagnose" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        front = _frontmatter(
            sync_skills.render_skill(texto, "devin", name="sparkforge-diagnose")
        )
        assert "subagent" not in front
        assert "agent" not in front

    def test_a_contagem_das_duas_metades(self):
        assert len(sync_skills.DISPATCHABLE_SKILLS) >= 12
        assert len(sync_skills.NON_DISPATCHABLE_SKILLS) >= 8

    def test_as_do_d6_estao_todas_dentro(self):
        """O recorte literal do spec: os quatro `review-*` e os `analyze-*`."""
        d6 = {
            "review-emr-cluster",
            "review-data-validation",
            "review-glue-terraform",
            "review-pyspark-pr",
        } | {p.name for p in SKILL_DIRS if p.name.startswith("analyze-")}
        assert d6 <= set(sync_skills.DISPATCHABLE_SKILLS)


FRASE_INALCANCAVEL = "manutenção destrutiva só com confirmação explícita."


def secao_protocolo(texto: str) -> str:
    """O corpo da secao `## Protocolo` de uma skill, ou "" se ela nao existe.

    As vinte skills terminam com essa secao, e e o unico lugar delas que fala de
    fronteira. Ancorar nela e o mesmo criterio do teste de perfil: uma mencao de
    passagem no corpo -- `optimize-iceberg-table` tem uma secao inteira sobre
    `expire_snapshots` nao ter rollback -- e conhecimento de dominio, nao
    declaracao de fronteira.
    """
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        if linha.strip() == "## Protocolo":
            fim = i + 1
            while fim < len(linhas) and not linhas[fim].startswith("## "):
                fim += 1
            return "\n".join(linhas[i + 1 : fim])
    return ""


def falta_fronteira_de_despacho(texto: str) -> str | None:
    """O que falta para a skill declarar a fronteira, ou None se nao falta nada.

    **Medido antes de escrever** (revisao final da fase): `## Nao faz` aparece em
    **0 das 20** skills, nenhuma das **12** despachaveis dizia "nao executa" nem
    para onde a confirmacao vai, e **12 de 12** terminavam em
    *"manutencao destrutiva so com confirmacao explicita"* -- sem dizer com quem.

    Essa frase e o defeito, nao a base: dentro de um subagente ela manda obter
    algo **inalcancavel** (`ask_user_question` e sempre negado a subagente,
    V-DV-10). Por isso o criterio tem quatro partes e a primeira e uma AUSENCIA:

    1. A frase antiga nao pode ter sobrado. Acrescentar a correcao ao lado dela
       deixaria as duas instrucoes no mesmo paragrafo, e a errada primeiro.
    2. `destrutiv`, que nomeia o ato.
    3. `não executa`, que e a metade que o subagente pode cumprir sozinho.
    4. `sobe`, que nomeia para onde a decisao vai. As duas metades falham de
       formas diferentes e as duas falham MUDAS: quem so recusa para sem dizer
       por que; quem so aponta o destino segue sem confirmar.

    A fronteira do D-4 vive no perfil, e o spec a chama de "segunda rede" do D-6.
    Nas **nove** despachaveis sem `agent:` essa rede pode nao estar em escopo: o
    Devin escolhe o perfil, e a escolha inclui o built-in `subagent_general`, que
    tem acesso total e nenhum `## Nao faz`. Nessas nove a skill e a unica rede.
    """
    secao = secao_protocolo(texto)
    if not secao:
        return "sem secao `## Protocolo`"
    if FRASE_INALCANCAVEL in secao:
        return "`## Protocolo` ainda manda obter confirmação inalcançável"
    faltando = [r for r in ("destrutiv", "não executa", "sobe") if r not in secao]
    return f"`## Protocolo` sem {' nem '.join(faltando)}" if faltando else None


class TestFronteiraNaSkillDespachavel:
    """A fronteira do D-4 nao alcanca a unidade que o Devin despacha.

    O que o Devin despacha por `subagent: true` e a **skill**, e o perfil so
    entra quando `agent:` o nomeia -- em tres das doze. Nas outras nove o
    roteamento e do harness, e ele pode cair num built-in sem fronteira nenhuma.
    Logo a declaracao tem que estar na skill, que e a unidade despachada.
    """

    def test_o_recorte_nao_e_vazio(self):
        """Guarda contra o teste que passa sem olhar nada: se
        `DISPATCHABLE_SKILLS` esvaziasse, o parametrizado abaixo sumiria."""
        assert len(sync_skills.DISPATCHABLE_SKILLS) >= 12

    @pytest.mark.parametrize("nome", sorted(sync_skills.DISPATCHABLE_SKILLS))
    def test_despachavel_declara_a_fronteira(self, nome):
        problema = falta_fronteira_de_despacho(
            (SKILLS / nome / "SKILL.md").read_text(encoding="utf-8")
        )
        assert problema is None, f"skills/{nome}/SKILL.md: {problema}"

    def test_a_frase_antiga_sozinha_nao_conta(self):
        """O estado exato em que as doze estavam, e o motivo de a primeira parte
        do criterio ser uma ausencia: a instrucao antiga precisava ser
        CORRIGIDA, nao duplicada."""
        texto = f"## Protocolo\n\nSiga `AGENT_PROTOCOL.md`. Resumo: {FRASE_INALCANCAVEL}\n"
        assert (
            falta_fronteira_de_despacho(texto)
            == "`## Protocolo` ainda manda obter confirmação inalcançável"
        )

    def test_meia_fronteira_nao_conta(self):
        """Recusar sem dizer para onde a decisao vai e a skill que para sem
        explicar."""
        texto = "## Protocolo\n\nManutenção destrutiva você não executa.\n"
        assert falta_fronteira_de_despacho(texto) == "`## Protocolo` sem sobe"

    def test_skill_sem_a_secao_e_pega(self):
        assert (
            falta_fronteira_de_despacho("---\nname: nova\n---\n\nCorpo.\n")
            == "sem secao `## Protocolo`"
        )

    def test_mencao_fora_da_secao_nao_conta(self):
        texto = (
            "## Manutenção destrutiva\n\n"
            "Você não executa `expire_snapshots`; a confirmação sobe ao pai.\n\n"
            "## Protocolo\n\nSiga `AGENT_PROTOCOL.md`.\n"
        )
        assert falta_fronteira_de_despacho(texto) == (
            "`## Protocolo` sem destrutiv nem não executa nem sobe"
        )


class TestSkillsReais:
    """As vinte skills que o espelho do Devin vai receber."""

    def test_o_corpus_tem_vinte_skills(self):
        assert len(SKILL_DIRS) >= 20

    def test_claude_e_github_recebem_byte_a_byte(self):
        """`.claude/skills/` continua passthrough: o Claude Code nao le
        `subagent:`, e publicar campo que ninguem consome e ruido no diff."""
        for skill in SKILL_DIRS:
            texto = (skill / "SKILL.md").read_text(encoding="utf-8")
            for plataforma in ("claude", "github"):
                assert (
                    sync_skills.render_skill(texto, plataforma, name=skill.name)
                    == texto
                ), skill.name

    def test_despachavel_ganha_subagent_true(self):
        for skill in SKILL_DIRS:
            if skill.name not in sync_skills.DISPATCHABLE_SKILLS:
                continue
            texto = (skill / "SKILL.md").read_text(encoding="utf-8")
            front = _frontmatter(
                sync_skills.render_skill(texto, "devin", name=skill.name)
            )
            assert front["subagent"] == "true", skill.name

    def test_nao_despachavel_nao_ganha_campo_nenhum(self):
        for skill in SKILL_DIRS:
            if skill.name in sync_skills.DISPATCHABLE_SKILLS:
                continue
            texto = (skill / "SKILL.md").read_text(encoding="utf-8")
            front = _frontmatter(
                sync_skills.render_skill(texto, "devin", name=skill.name)
            )
            assert "subagent" not in front, skill.name
            assert "agent" not in front, skill.name

    def test_agent_so_aparece_onde_ha_um_coordenador_so(self):
        com_agent = {}
        for skill in SKILL_DIRS:
            texto = (skill / "SKILL.md").read_text(encoding="utf-8")
            front = _frontmatter(
                sync_skills.render_skill(texto, "devin", name=skill.name)
            )
            if "agent" in front:
                com_agent[skill.name] = front["agent"]
        assert com_agent == {
            "analyze-graph-data": "sf-graph-specialist",
            "review-emr-cluster": "emr-infra-reviewer",
            "verify-agent-evidence": "sf-evidence-verifier",
            "engineer-agent-context": "sf-context-engineer",
            "engineer-agent-memory": "sf-memory-engineer",
        }

    def test_o_frontmatter_sobrevive_a_insercao(self):
        """O risco simetrico da Task 1: la a remocao podia deixar continuacao
        orfa; aqui a insercao pode cair no lugar errado. As chaves que ja
        existiam continuam existindo, com o mesmo valor, e as unicas novas sao
        as que a renderizacao controla."""
        for skill in SKILL_DIRS:
            texto = (skill / "SKILL.md").read_text(encoding="utf-8")
            antes = _frontmatter(texto)
            depois = _frontmatter(
                sync_skills.render_skill(texto, "devin", name=skill.name)
            )
            assert antes["name"] == skill.name
            assert antes["description"]
            assert all(depois[k] == v for k, v in antes.items()), skill.name
            novas = set(depois) - set(antes)
            assert novas <= {"subagent", "agent"}, (skill.name, novas)

    def test_os_campos_entram_antes_da_cerca_de_fechamento(self):
        for skill in sync_skills.DISPATCHABLE_SKILLS:
            texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
            linhas = sync_skills.render_skill(texto, "devin", name=skill).splitlines()
            assert linhas.index("subagent: true") < linhas.index("---", 1), skill

    def test_o_corpo_sobrevive_inteiro(self):
        for skill in SKILL_DIRS:
            texto = (skill / "SKILL.md").read_text(encoding="utf-8")
            corpo = texto.split("\n---\n", 1)[1]
            assert corpo in sync_skills.render_skill(texto, "devin", name=skill.name)

    def test_render_e_idempotente(self):
        for skill in SKILL_DIRS:
            texto = (skill / "SKILL.md").read_text(encoding="utf-8")
            once = sync_skills.render_skill(texto, "devin", name=skill.name)
            assert sync_skills.render_skill(once, "devin", name=skill.name) == once


class TestBordasDeSkill:
    def test_skill_desconhecida_falha_alto(self):
        """Skill sem decisao registrada nao vira "nao despacha" em silencio."""
        with pytest.raises(ValueError, match="sem decisao de despacho"):
            sync_skills.render_skill(
                SKILL_SINTETICA, "devin", name="skill-que-nao-existe"
            )

    def test_plataforma_desconhecida_falha_alto(self):
        with pytest.raises(ValueError, match="plataforma desconhecida"):
            sync_skills.render_skill(
                SKILL_SINTETICA, "cursor", name="review-emr-cluster"
            )

    def test_campo_posto_a_mao_e_removido_de_quem_nao_despacha(self):
        """A renderizacao REMOVE antes de inserir. Sem isso, `subagent: true`
        escrito a mao no espelho de `sparkforge-diagnose` sobreviveria a toda
        regeneracao, e o gate nunca acusaria."""
        adulterada = SKILL_SINTETICA.replace(
            "description: Use quando.\n",
            "description: Use quando.\nsubagent: true\nagent: perfil-inventado\n",
        )
        out = sync_skills.render_skill(adulterada, "devin", name="sparkforge-diagnose")
        assert "subagent" not in _yaml_estrito(out)
        assert "agent" not in _yaml_estrito(out)
        assert "Corpo da skill." in out

    def test_campo_posto_a_mao_e_reescrito_em_quem_despacha(self):
        adulterada = SKILL_SINTETICA.replace(
            "description: Use quando.\n",
            "description: Use quando.\nagent: perfil-inventado\n",
        )
        out = sync_skills.render_skill(adulterada, "devin", name="review-emr-cluster")
        assert _yaml_estrito(out)["agent"] == "emr-infra-reviewer"
        assert "perfil-inventado" not in out

    def test_sem_frontmatter_sai_inalterado(self):
        texto = "Sem cerca nenhuma.\nsubagent: true\n"
        assert (
            sync_skills.render_skill(texto, "devin", name="review-emr-cluster") == texto
        )

    def test_fim_de_linha_e_preservado(self):
        """A linha INSERIDA usa o fim de linha do arquivo. Misturar LF e CRLF no
        mesmo frontmatter faria o espelho divergir a cada regeneracao numa arvore
        com autocrlf."""
        crlf = SKILL_SINTETICA.replace("\n", "\r\n")
        out = sync_skills.render_skill(crlf, "devin", name="review-emr-cluster")
        assert "subagent: true\r\n" in out
        assert "\n" not in out.replace("\r\n", "")

    def test_lista_indentada_no_fim_do_frontmatter_nao_engole_o_campo(self):
        """Borda que a insercao no fim tem que respeitar: se a ultima chave for
        lista de bloco, o campo novo nao pode sair indentado nem depois da
        cerca."""
        com_lista = (
            "---\nname: review-emr-cluster\ndescription: Use quando.\n"
            "triggers:\n  - user\n  - model\n---\n\nCorpo da skill.\n"
        )
        out = sync_skills.render_skill(com_lista, "devin", name="review-emr-cluster")
        front = _yaml_estrito(out)
        assert front["triggers"] == ["user", "model"]
        assert front["subagent"] is True
        assert front["agent"] == "emr-infra-reviewer"


def _quebras(agent_por_skill: dict, skills_por_perfil: dict) -> list[str]:
    """As duas metades do invariante bidirecional, num lugar so.

    Relacao que quebra de UM LADO SO e a familia de defeito que a Fase 5c achou
    nas duas listas `EXTRACTORS` mantidas a mao: ou o perfil some e o `agent:`
    fica apontando para nada, ou o perfil deixa de declarar a skill e o `agent:`
    segue nomeando quem nao a coordena mais.
    """
    problemas = []
    for skill, perfil in sorted(agent_por_skill.items()):
        if perfil not in skills_por_perfil:
            problemas.append(f"{skill}: agent nomeia perfil inexistente: {perfil}")
        elif skill not in skills_por_perfil[perfil]:
            problemas.append(f"{skill}: o perfil {perfil} nao declara esta skill")
    return problemas


class TestInvarianteBidirecional:
    """Criterio 4 do spec, medido sobre o ESPELHO em disco -- nao sobre a funcao
    que o gerou. Espelho editado a mao e perfil renomeado sao pegos aqui."""

    def _agent_por_skill(self) -> dict:
        espelho = ROOT / ".agents" / "skills"
        fronts = {
            p.parent.name: _frontmatter(p.read_text(encoding="utf-8"))
            for p in sorted(espelho.glob("*/SKILL.md"))
        }
        return {
            nome: front["agent"] for nome, front in fronts.items() if "agent" in front
        }

    def _skills_por_perfil(self) -> dict:
        return {
            perfil.stem: set(
                _lista_de_topo(perfil.read_text(encoding="utf-8"), "skills")
            )
            for perfil in sorted(AGENTS.glob("*.md"))
        }

    def test_agent_de_skill_nomeia_perfil_que_a_declara(self):
        quebras = _quebras(self._agent_por_skill(), self._skills_por_perfil())
        assert not quebras, quebras

    def test_o_invariante_nao_e_vazio(self):
        """Recorte que esvaziasse o lado esquerdo passaria sem olhar nada.

        Eram tres ate a revisao final de 2026-08-04; `diagnose-oom` saiu porque
        o declarante unico dela era o orquestrador, e a unicidade vinha de uma
        omissao no `skills:` de `spark-performance-architect`."""
        assert len(self._agent_por_skill()) >= 5

    def test_perfil_que_sumiu_e_pego(self):
        assert _quebras(
            {"review-emr-cluster": "perfil-apagado"}, self._skills_por_perfil()
        )

    def test_perfil_que_deixou_de_declarar_e_pego(self):
        assert _quebras(
            {"review-emr-cluster": "iceberg-performance-engineer"},
            self._skills_por_perfil(),
        )
