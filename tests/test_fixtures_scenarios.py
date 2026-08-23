"""Corpus de CENARIO: um job inteiro atravessando um par de versoes de Glue.

O que este corpus prova que `fixtures/migration/` nao prova
-----------------------------------------------------------

Todo golden de `fixtures/migration/` (e de `fixtures/infra_code/`) existe para
fazer UMA regra disparar, sobre UM artefato, num runtime UNICO escrito a mao no
`meta.yaml` e passado direto para `judge()`. Isso prova a regra. Nao prova o
produto: ninguem opera este repositorio perguntando "o que `mig.sdk_import`
vira" -- pergunta-se "o que acontece com ESTE job se eu sair do Glue 4.0 para o
6.0". A resposta atravessa `sparkforge/migration/assessment.py`, que expande o
par em degraus, julga cada degrau com o runtime derivado da MATRIZ (nao do
`meta.yaml`) e agrega o resultado em tres visoes com cardinalidades diferentes
(`findings`, `by_step`, `report()`).

Nada disso era exercitado ponta a ponta por golden nenhum. `assess()` tinha
testes de unidade (`tests/test_migration_assessment.py`) construidos sobre
fixtures de duas linhas montadas em `tmp_path`; um corpus versionado de job
realista, com mais de um artefato e mais de um tipo de artefato, nao existia.

O golden e o `to_dict()` do `MigrationAssessment`, e nao `facts`+`findings`,
porque e ele que carrega a informacao que so o cenario produz: em QUAL degrau
cada achado nasceu. Um golden de findings responderia "quais problemas", que os
goldens por kind ja respondem; `by_step` responde "e a partir de onde", que e o
que decide se um salto intermediario resolve parte do problema.

Por que so tres cenarios
------------------------

O prompt lista catorze casos possiveis (Sec. 38). Um cenario que nao dispara
regra nenhuma e fixture que nao prova nada -- e o repositorio ja tem gate que
cobra golden POR REGRA
(`tests/test_fixtures_kind_coverage.py::test_every_rule_has_a_fixture_that_fires_it`),
entao cobertura de regra nao e o que falta aqui. Os tres escolhidos cobrem tres
eixos que nao se substituem:

  * `glue_51_para_60_iceberg_ansi` -- um degrau so, varios kinds, um deles sem
    regra nenhuma: prova o que o par NAO sustenta tanto quanto o que sustenta.
  * `glue_40_para_60_salto_longo` -- tres degraus, cinco regras nascendo em
    degraus diferentes: prova a acumulacao e a deduplicacao no mesmo caso.
  * `glue_60_fgac_com_jar` -- artefato de INFRAESTRUTURA e regra de outra area
    (`SF-LF`) atravessando o mesmo motor: prova que `assess()` julga o catalogo
    inteiro por degrau, nao so `SF-MIG`.

Os cenarios de holdout (`evals/holdout/`) usam este mesmo formato, e este runner
NAO os le -- ver `tests/test_evals_holdout.py` e `evals/holdout/README.md`.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.migration import extract_migration_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.migration.assessment import assess

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "scenarios"

REQUIRED_FIXTURES = {
    "glue_51_para_60_iceberg_ansi",
    "glue_40_para_60_salto_longo",
    "glue_60_fgac_com_jar",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def extract(directory: Path):
    """A MESMA extracao de `scripts/regen_fixtures.py::regen_scenario`.

    Codigo (`.py`, `.jar`, `requirements*.txt`) sempre; infraestrutura (`.tf`)
    quando existe, no molde de `regen_graph`. Um cenario com os dois julga a
    uniao, que e o que o operador tem em maos.
    """
    input_dir = directory / "input"
    facts = list(extract_migration_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
    return facts


def run_scenario(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract(directory)
    resultado = assess(facts, source=str(meta["source"]), target=str(meta["target"]))
    return meta, facts, resultado


def golden(directory: Path):
    return json.loads((directory / "expected" / "assessment.json").read_text(encoding="utf-8"))


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio vazio, o
# pytest 8.x invoca o callable sobre o sentinela NOTSET durante a coleta e
# aborta a sessao INTEIRA. Mesma guarda de `test_fixtures_golden_migration.py`.
@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
class TestGolden:
    def test_assessment_matches_golden(self, directory):
        _, _, resultado = run_scenario(directory)
        assert resultado.to_dict() == golden(directory)

    def test_declared_rules_are_exactly_the_ones_that_fire(self, directory):
        """Igualdade nos DOIS sentidos, nao inclusao.

        `expects_rules` que omite uma regra que dispara e um cenario que mudou
        de significado sem ninguem perceber -- e exatamente o caso que o
        `proves` de cada `meta.yaml` existe para nomear.
        """
        meta, _, resultado = run_scenario(directory)
        assert sorted({f.rule_id for f in resultado.findings}) == sorted(meta["expects_rules"])

    def test_the_declared_pair_is_the_pair_that_was_judged(self, directory):
        meta, _, resultado = run_scenario(directory)
        assert resultado.source == str(meta["source"])
        assert resultado.target == str(meta["target"])
        assert resultado.steps[0][0] == str(meta["source"])
        assert resultado.steps[-1][1] == str(meta["target"])

    def test_extraction_is_deterministic(self, directory):
        primeiro = [f.to_dict() for f in extract(directory)]
        segundo = [f.to_dict() for f in extract(directory)]
        assert primeiro == segundo

    def test_the_whole_assessment_is_deterministic(self, directory):
        """Determinismo do RESULTADO, nao so da extracao.

        A extracao ordenada nao garante o agregado: `report()` deduplica por
        dicionario e escolhe a instancia mais severa, e uma ordem de iteracao
        instavel ali trocaria qual instancia entra no relatorio sem mudar
        nenhum fact.
        """
        assert run_scenario(directory)[2].to_dict() == run_scenario(directory)[2].to_dict()

    def test_every_fact_is_anchored_in_an_artifact_of_the_fixture(self, directory):
        """Um cenario e um conjunto de artefatos; um fact sem artefato dentro
        de `input/` veio de outro lugar, e o golden estaria descrevendo um job
        que ninguem versionou."""
        _, facts, _ = run_scenario(directory)
        assert facts, "cenario sem fact nenhum nao exercita o motor"
        for fact in facts:
            artefato = fact.provenance["artifact"]
            assert (directory / "input" / artefato).exists(), artefato

    def test_the_meta_says_what_the_scenario_proves(self, directory):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        assert meta["name"] == directory.name
        assert len(meta.get("proves", "").strip()) >= 200, (
            "`proves` existe para dizer o que ESTE cenario prova que os goldens "
            "por kind nao provam; uma linha generica nao diz isso."
        )

    def test_no_gate_that_needs_a_real_run_is_ever_pass(self, directory):
        """Invariante do motor, medido no cenario: nenhuma execucao real foi
        coletada, entao os quatro gates de execucao nascem BLOCKED e a
        recomendacao nunca pode ser GO."""
        _, _, resultado = run_scenario(directory)
        for nome in ("dados", "performance", "custo", "canary"):
            assert resultado.gates[nome] == "BLOCKED", nome
            assert resultado.missing_evidence[nome]
        assert resultado.recommendation != "GO"


class TestAcumulacaoPorDegrau:
    """O cenario 2 e o unico com caminho de mais de um degrau, e por isso o
    unico que pode medir o que `assess()` acrescenta ao `judge()`."""

    @staticmethod
    def _salto_longo():
        return run_scenario(FIXTURES / "glue_40_para_60_salto_longo")

    def test_o_par_expande_nos_tres_degraus_da_matriz(self):
        _, _, resultado = self._salto_longo()
        assert resultado.steps == [("4.0", "5.0"), ("5.0", "5.1"), ("5.1", "6.0")]

    def test_o_mesmo_problema_nasce_em_mais_de_um_degrau(self):
        """DECISAO 1 de `sparkforge/migration/assessment.py`, medida num job
        realista em vez de num fact sintetico: SF-MIG-001 e SF-MIG-002 tem
        `runtime_scope` de Glue 5.0 para cima, e os TRES degraus deste caminho
        tem alvo que satisfaz esse escopo -- entao as duas nascem tres vezes.
        Deduplicar aqui apagaria a informacao de que o breaking change continua
        valendo depois do proximo salto."""
        _, _, resultado = self._salto_longo()
        por_regra: dict[str, list] = {}
        for finding, degrau in resultado.by_step:
            por_regra.setdefault(finding.rule_id, []).append(degrau)
        assert por_regra["SF-MIG-001"] == resultado.steps
        assert por_regra["SF-MIG-002"] == resultado.steps

    def test_o_relatorio_mostra_o_mesmo_problema_uma_vez_so(self):
        """DECISAO 1b: `report()` responde a pergunta de quem LE -- "quantos
        problemas eu tenho?" -- e o mesmo problema tres vezes, porque o caminho
        tem tres degraus, faria este assessment parecer tres vezes pior que o
        mesmo job de 5.1 para 6.0 sem que nada de fato seja pior."""
        _, _, resultado = self._salto_longo()
        relatorio = resultado.report()
        assert len(resultado.by_step) == 9
        assert len(relatorio) == 5
        por_regra = {r.finding.rule_id: r for r in relatorio}
        assert sorted(por_regra) == sorted({f.rule_id for f in resultado.findings})
        assert por_regra["SF-MIG-001"].steps == resultado.steps
        assert por_regra["SF-MIG-002"].steps == resultado.steps

    def test_a_deduplicacao_nao_perde_em_qual_degrau_o_problema_vale(self):
        """Deduplicar sem dizer ONDE vale trocaria ruido por perda de
        informacao: a uniao dos `steps` do relatorio precisa devolver
        exatamente os pares de `by_step`, um a um."""
        _, _, resultado = self._salto_longo()
        do_relatorio = sorted(
            (r.finding.rule_id, degrau) for r in resultado.report() for degrau in r.steps
        )
        do_by_step = sorted((f.rule_id, degrau) for f, degrau in resultado.by_step)
        assert do_relatorio == do_by_step

    def test_cada_regra_nasce_no_primeiro_degrau_que_cruza_a_sua_fronteira(self):
        """O que o cenario existe para medir: as cinco regras NAO nascem
        juntas. As de Glue 5.0 para cima nascem no primeiro degrau; as de
        Glue 6.0 e as de Spark 4 so no ultimo, porque so ali o alvo do degrau
        cruza a fronteira delas."""
        _, _, resultado = self._salto_longo()
        primeiro: dict[str, tuple[str, str]] = {}
        for finding, degrau in resultado.by_step:
            primeiro.setdefault(finding.rule_id, degrau)
        assert primeiro == {
            "SF-MIG-001": ("4.0", "5.0"),
            "SF-MIG-002": ("4.0", "5.0"),
            "SF-MIG-003": ("5.1", "6.0"),
            "SF-SPARK4-003": ("5.1", "6.0"),
            "SF-SPARK4-004": ("5.1", "6.0"),
        }

    def test_um_degrau_so_nao_deduplica_nada(self):
        """O contrafactual do cenario 1: com um degrau unico, `by_step` e
        `report()` tem a mesma cardinalidade -- a deduplicacao so tem o que
        fazer quando o caminho tem mais de um degrau."""
        _, _, resultado = run_scenario(FIXTURES / "glue_51_para_60_iceberg_ansi")
        assert len(resultado.steps) == 1
        assert len(resultado.by_step) == len(resultado.report()) == 1


class TestAdversarial:
    def test_o_cenario_de_um_degrau_nao_dispara_o_que_o_par_nao_sustenta(self):
        """`glue_51_para_60_iceberg_ansi` carrega `mig.python_dep`
        (`pyarrow==17.0.0`) e `mig.table_format`, e nenhum dos dois vira
        achado: o primeiro porque 17 satisfaz o piso 15.0.0 que SF-SPARK4-003
        cobra no Spark 4.1 -- negativo por VALOR, com o degrau CRUZANDO a
        fronteira de versao -- e o segundo porque nenhuma regra do catalogo o
        consome. Fact presente sem regra nao pode virar achado."""
        _, facts, resultado = run_scenario(FIXTURES / "glue_51_para_60_iceberg_ansi")
        kinds = {f.kind for f in facts}
        assert {"mig.python_dep", "mig.table_format", "mig.ansi_risk"} <= kinds
        assert {f.rule_id for f in resultado.findings} == {"SF-MIG-003"}

    def test_varios_casts_no_mesmo_arquivo_viram_um_achado_so(self):
        """`same_subject` agrupa por arquivo: um job com dez `cast(` sem guarda
        tem um problema, nao dez."""
        _, facts, resultado = run_scenario(FIXTURES / "glue_51_para_60_iceberg_ansi")
        assert len([f for f in facts if f.kind == "mig.ansi_risk"]) == 2
        assert len([f for f in resultado.findings if f.rule_id == "SF-MIG-003"]) == 1

    def test_o_cenario_de_terraform_nao_e_julgado_por_sf_mig_004(self):
        """SF-MIG-004 acusa MUDANCA de `glue_version`, e mudanca so existe em
        fact vindo de `extract_terraform_diff` (`attrs.changed`). Um `.tf`
        sozinho nao tem estado anterior. O cenario documenta a fronteira em vez
        de esconde-la: a regra que existe para acusar migracao de runtime nao
        ve a migracao que este cenario avalia."""
        _, facts, resultado = run_scenario(FIXTURES / "glue_60_fgac_com_jar")
        versao = [
            f for f in facts if f.kind == "tf.attribute" and f.attrs.get("key") == "glue_version"
        ]
        assert versao, "a fixture perdeu o atributo que a regra procura"
        assert all(not f.attrs.get("changed") for f in versao)
        assert "SF-MIG-004" not in {f.rule_id for f in resultado.findings}

    def test_uma_regra_de_outra_area_atravessa_o_motor_de_migracao(self):
        """`assess()` chama `judge()` com o catalogo INTEIRO uma vez por degrau.
        SF-LF-001 e de `rules/catalog/lakeformation.yaml`, nao de `SF-MIG`, e
        chega ao relatorio pelo degrau cujo alvo satisfaz a fronteira dela.

        E fecha o eixo DELA, nao o de compatibilidade: desde a fase H2 o
        contrato tem eixo `lakeformation`, e um achado move um eixo so -- se
        `SF-LF-001` movesse tambem `compatibilidade`, o mesmo problema fechando
        dois gates pareceria dois problemas."""
        _, _, resultado = run_scenario(FIXTURES / "glue_60_fgac_com_jar")
        achado = next(f for f in resultado.findings if f.rule_id == "SF-LF-001")
        assert achado.severity == "P0"
        assert resultado.gates["lakeformation"] == "FAIL"
        assert resultado.recommendation == "NO_GO"

    def test_todo_cenario_dispara_ao_menos_uma_regra(self):
        """Cenario que nao dispara regra nenhuma e fixture que nao prova nada.
        O corpus tem gate por regra em outro lugar; aqui o que se cobra e que
        cada cenario exercite o motor de verdade."""
        for directory in fixture_dirs():
            meta, _, resultado = run_scenario(directory)
            assert resultado.findings, directory.name
            assert meta["expects_rules"], directory.name

    def test_o_golden_nao_carrega_par_de_versoes_que_a_matriz_desconhece(self):
        """Guarda contra golden regenerado a partir de um `meta.yaml` editado a
        mao: todo degrau do golden precisa ser um degrau que a matriz produz."""
        from sparkforge.migration import version_path

        for directory in fixture_dirs():
            dado = golden(directory)
            esperado = version_path.steps(dado["source_runtime"], dado["target_runtime"])
            assert [list(s) for s in esperado] == dado["steps"], directory.name
