"""Glue 4.0, 5.0 e 5.1: a matriz e o escopo das regras nos runtimes correntes.

Dois riscos distintos, um modulo:

1. **Deriva entre codigo e documento.** `GLUE_MATRIX` e a tabela de
   `knowledge/glue/runtime-matrix.md` sao a MESMA informacao escrita duas
   vezes. `test_runtime_detect.py` fixa valores literais no teste, o que pega
   uma mudanca acidental no codigo mas nao pega o codigo e o documento se
   afastando -- e e o documento que o agente le para recomendar. Aqui a tabela
   do markdown e parseada e comparada com o dicionario.

2. **Regra fora de escopo em silencio.** `runtime_scope` faz o motor pular a
   regra ANTES de olhar fact nenhum, e o operador nao ve diferenca entre
   "avaliei e nao achei" e "nem avaliei". Uma guarda escrita errada (`>=5.0`
   onde se queria `>=4.0`) apaga a regra do relatorio inteiro nos runtimes
   correntes sem nenhum sinal. Este modulo enumera, por versao, exatamente
   quais regras ficam fora -- e cada excecao tem que estar justificada abaixo.
"""
import re
from pathlib import Path

import pytest

from sparkforge.facts.runtime_detect import GLUE_MATRIX, detect_runtime
from sparkforge.rules.loader import catalog_dir, load_catalog
from sparkforge.rules.version_scope import in_scope

ROOT = Path(__file__).resolve().parents[1]
MATRIX_DOC = ROOT / "knowledge" / "glue" / "runtime-matrix.md"

# Os runtimes correntes. Glue 3.0 esta fora desta lista de proposito: continua
# na matriz (jobs antigos existem) mas nao e alvo de recomendacao nova.
CURRENT = ("4.0", "5.0", "5.1")

# Regras que NAO sao avaliadas em cada versao corrente, com a razao. Uma regra
# que apareca aqui sem justificativa e uma regra apagada do relatorio.
#
#   SF-ENV-002  `glue: ">=5.1"` + `iceberg: ">=1.10.0"` -- a armadilha do
#               format V3 do Iceberg, que so existe a partir de 5.1. Em 4.0 e
#               5.0 nao ha V3 para escrever, entao pular e correto.
#
#   SF-GRAPH-002 `spark: [">=3.3", "<3.4"]` -- "nao ha artefato de GraphFrames
#               publicado para este Spark". Glue 4.0 e Spark 3.3.0 e e a UNICA
#               das tres correntes sem jar, entao ela e avaliada la e pulada em
#               5.0 (3.5.4) e 5.1 (3.5.6), onde ha `0.8.3-spark3.5` e a serie
#               `io.graphframes` inteira. Esta e a direcao que doi ao contrario
#               das outras: se ela aparecer em 4.0, a faixa esta errada, e as
#               nove celulas sem jar ficam sem cobertura.
#
# SF-ENV-004 ESTAVA aqui, com `glue: "<4.0"`, e saiu na Task 3c da Fase 5a. O
# guarda estava na camada errada: a condicao do `when` e `attrs.spark_minor <
# 3.2`, puramente Spark, e um EMR com Spark 3.1.1 nao tem chave `glue` -- a
# regra era apagada justamente onde e mais necessaria. Hoje ela tem
# `runtime_scope: {}` e e AVALIADA em 4.0, 5.0 e 5.1; nao dispara em nenhuma
# porque as tres resolvem para Spark >= 3.3, o que a CONDICAO barra. A fronteira
# do AQE continua fixada nos dois sentidos por
# `test_fixtures_golden_runtime.py::test_aqe_boundary_holds_on_both_sides`.
#
# SF-MIG-001  `glue: ">=5.0"` -- import de AWS SDK v1 sobrevivendo num runtime
#             que deixa de garantir o classpath v1. A quebra so existe A
#             PARTIR do Glue 5.0 (Java 8 -> Java 17), entao em 4.0 ela e
#             corretamente fora de escopo: nao ha classpath novo para faltar.
#
# SF-MIG-002  `glue: ">=5.0"` -- chave exclusiva do EMRFS sobrevivendo num
#             runtime que le S3A, nao EMRFS. O S3A so vira o sistema de
#             arquivos padrao A PARTIR do Glue 5.0; em 4.0 o EMRFS ainda le a
#             chave, entao nao ha risco de configuracao inerte para acusar.
#
# SF-MIG-003  `glue: ">=6.0"` -- cast sem guarda sob ANSI mode (Task 11 desta
#             fase, confirmado contra migrating-version-60.html). Nenhuma das
#             tres versoes CORRENTES (4.0, 5.0, 5.1) chega no Glue 6.0, entao
#             ela fica fora de escopo nas tres -- e a unica regra do catalogo
#             que hoje nao dispara em runtime corrente nenhum, o que e correto:
#             a fronteira do ANSI mode ainda nao foi cruzada por nenhum deles.
#
# SF-SPARK4-001/002 `spark: ">=4.0.0"` e SF-SPARK4-003 `spark: ">=4.1.0"` --
#             config renomeada, API de pandas-on-Spark removida e piso do
#             PyArrow. As tres fronteiras sao do APACHE, nao do empacotamento
#             da AWS, entao o guarda e por versao de SPARK: 4.0 resolve para
#             Spark 3.3.0, 5.0 para 3.5.4 e 5.1 para 3.5.6, todas abaixo de
#             4.0.0. Ficam fora de escopo nas tres correntes pelo mesmo motivo
#             que SF-MIG-003 -- a fronteira ainda nao foi cruzada por nenhuma
#             delas -- e sao avaliadas em Glue 6.0 (Spark 4.1.1), que esta na
#             matriz mas fora de `CURRENT`.
EXPECTED_OUT_OF_SCOPE = {
    "4.0": {
        "SF-ENV-002",
        "SF-MIG-001",
        "SF-MIG-002",
        "SF-MIG-003",
        "SF-SPARK4-001",
        "SF-SPARK4-002",
        "SF-SPARK4-003",
    },
    "5.0": {
        "SF-ENV-002",
        "SF-GRAPH-002",
        "SF-MIG-003",
        "SF-SPARK4-001",
        "SF-SPARK4-002",
        "SF-SPARK4-003",
    },
    "5.1": {
        "SF-GRAPH-002",
        "SF-MIG-003",
        "SF-SPARK4-001",
        "SF-SPARK4-002",
        "SF-SPARK4-003",
    },
}


def _doc_matrix() -> dict[str, dict[str, str]]:
    """Le a tabela principal de `runtime-matrix.md`.

    Formato esperado por linha:
    `| 5.0 | 3.5.4 | 3.11 | 2.12 | 1.7.1 | 0.15.0 | 3.3.0 |`
    """
    parsed: dict[str, dict[str, str]] = {}
    for line in MATRIX_DOC.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not re.fullmatch(r"\d+\.\d+", cells[0]):
            continue
        parsed[cells[0]] = {"spark": cells[1], "python": cells[2], "iceberg": cells[4]}
    return parsed


def _rules():
    return [r for r in load_catalog(catalog_dir()) if r["id"].startswith("SF-")]


class TestMatrixMatchesTheCommittedKnowledge:
    def test_the_doc_table_is_parseable_at_all(self):
        """Guarda contra o teste passar por ter lido zero linhas."""
        assert set(_doc_matrix()) >= set(CURRENT)

    @pytest.mark.parametrize("version", CURRENT)
    def test_code_matrix_equals_doc_table(self, version):
        assert GLUE_MATRIX[version] == _doc_matrix()[version], version

    def test_no_version_exists_in_code_but_not_in_the_doc(self):
        """Uma linha so no codigo e uma versao que o agente nunca vai citar
        certo, porque ele le o documento."""
        assert set(GLUE_MATRIX) <= set(_doc_matrix())


class TestDetectionOfTheCurrentRuntimes:
    @pytest.mark.parametrize("version", CURRENT)
    def test_glue_version_alone_resolves_the_whole_stack(self, version):
        context, facts = detect_runtime({"terraform": {"glue_version": version}})
        expected = GLUE_MATRIX[version]
        assert context.glue == version
        assert context.spark == expected["spark"]
        assert context.python == expected["python"]
        assert context.iceberg == expected["iceberg"]
        assert facts, version

    @pytest.mark.parametrize("version", CURRENT)
    def test_agreeing_event_log_is_not_a_divergence(self, version):
        context, _ = detect_runtime(
            {
                "terraform": {"glue_version": version},
                "event_log": {"spark_version": GLUE_MATRIX[version]["spark"]},
            }
        )
        assert list(context.divergences) == []

    @pytest.mark.parametrize("version", CURRENT)
    def test_disagreeing_event_log_is_always_a_divergence(self, version):
        """A fonte observada ganha, mas o conflito e registrado. Em qualquer
        das tres versoes correntes -- nao so na que a fixture cobre."""
        context, _ = detect_runtime(
            {"terraform": {"glue_version": version}, "event_log": {"spark_version": "3.0.0"}}
        )
        assert context.spark == "3.0.0"
        assert context.divergences


class TestRuleScopeOnTheCurrentRuntimes:
    @pytest.mark.parametrize("version", CURRENT)
    def test_only_the_justified_rules_are_out_of_scope(self, version):
        context, _ = detect_runtime({"terraform": {"glue_version": version}})
        runtime = context.to_dict()
        out = {r["id"] for r in _rules() if not in_scope(r.get("runtime_scope") or {}, runtime)}
        assert out == EXPECTED_OUT_OF_SCOPE[version], version

    # Excecao de AREA INTEIRA, e nao regra a regra como EXPECTED_OUT_OF_SCOPE
    # acima.
    #
    # SF-MIG SAIU DAQUI quando SF-MIG-004 entrou. A excecao dizia que em Glue
    # 4.0 a area inteira fica muda, porque as tres regras de entao (001/002
    # `>=5.0`, 003 `>=6.0`) so valem depois de cruzar uma fronteira de versao
    # que o 4.0 antecede. SF-MIG-004 nao e desse tipo: ela afirma que o diff de
    # Terraform MUDOU `glue_version`, o que e verdade para qualquer par de
    # versoes e nao depende de runtime detectado nenhum -- por isso declara
    # `runtime_scope: {}` e e gateada por `requires_facts: [tf.attribute]`.
    # Com ela a area sobrevive ao guard em toda versao, e manter a excecao aqui
    # seria letra morta pre-aprovando um sumico que ja nao acontece.
    AREA_FULLY_OUT_OF_SCOPE: dict[str, set[str]] = {}

    @pytest.mark.parametrize("version", CURRENT)
    def test_every_area_of_the_catalog_survives_the_version_guard(self, version):
        """Nenhuma area inteira pode sumir num runtime corrente, exceto a
        declarada em `AREA_FULLY_OUT_OF_SCOPE` -- SF-ENV e a outra excecao, e
        mesmo ela mantem regra avaliavel nas tres."""
        context, _ = detect_runtime({"terraform": {"glue_version": version}})
        runtime = context.to_dict()
        surviving = {
            r["id"].rsplit("-", 1)[0]
            for r in _rules()
            if in_scope(r.get("runtime_scope") or {}, runtime)
        }
        # As areas sao derivadas do catalogo, nao listadas aqui: uma lista fixa
        # obriga a editar o teste ao criar area nova, e -- pior -- passa a
        # ESCONDER area nova que sumiu inteira no guard, porque ela nunca chegou
        # a entrar no conjunto esperado.
        all_areas = {r["id"].rsplit("-", 1)[0] for r in _rules()}
        esperado = all_areas - self.AREA_FULLY_OUT_OF_SCOPE.get(version, set())
        assert surviving == esperado, version

    def test_the_iceberg_v3_rule_is_scoped_to_51_and_only_51(self):
        """SF-ENV-002 guarda a armadilha do format V3 (Glue 5.1 escreve, Athena
        nao le). Alargar o escopo para 5.0 acusaria uma tabela que nao pode
        virar V3; estreitar apagaria o unico aviso sobre ela."""
        scopes = {r["id"]: r.get("runtime_scope") for r in _rules()}
        assert scopes["SF-ENV-002"] == {"glue": ">=5.1", "iceberg": ">=1.10.0"}

        for version, expected in (("4.0", False), ("5.0", False), ("5.1", True)):
            context, _ = detect_runtime({"terraform": {"glue_version": version}})
            assert in_scope(scopes["SF-ENV-002"], context.to_dict()) is expected, version
