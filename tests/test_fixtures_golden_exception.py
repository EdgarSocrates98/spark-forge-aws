"""Golden do corpus da excecao: o `Failure Reason` estruturado, e o que ele casa.

Arquivo dedicado, mesma razao dos demais `test_fixtures_golden_*.py`: o golden
guarda os facts de `sparkforge/facts/exception.py` (T1) e
`sparkforge/errors/matcher.py::build_signature_matches` (T2), mais os findings
de `rules/catalog/errors.yaml` (T3). Os dois modulos so entraram em
`tests/test_fixtures_kind_coverage.py::EXTRACTORS` no MESMO commit deste corpus,
e o comentario que os mantinha fora ate aqui era a divida nomeada que esta Task
fecha.

## A cadeia, e por que ela nao cabe num corpus de fonte unica

Nenhum dos dois modulos le artefato. `build_exceptions` estrutura o
`attrs.reason` de um `spark.stage.failure`, que so existe porque
`extract_event_log_path` leu um event log; `build_signature_matches` casa o
`spark.exception` que aquele produziu contra `knowledge/errors/`. E derivacao
pura sobre a UNIAO dos facts, no molde de `bridge.py` -- e por isso `_derive`
aqui tem a mesma forma do `_derive` de `test_fixtures_golden_bridge.py`.

As DUAS regras de `errors.yaml` esticam a cadeia mais um degrau: elas declaram
`mig.jar_binary` e `tf.attribute` em `requires_facts`, entao o corpus precisa de
TRES artefatos no mesmo `input/` -- `eventlog.jsonl`, `*.jar` e `*.tf`. O jar e o
Terraform entram sob guarda de existencia e nao por default, porque a diferenca
entre a fixture COM o jar e a fixture SEM ele e literalmente o que prova que
`requires_facts` faz trabalho.

## O corpus, por eixo

  * `excecao_simples` -- a forma canonica (classe no inicio da linha, frames
    indentados), mais `error.signature.unresolved` porque
    `IllegalArgumentException` nao casa assinatura nenhuma.
  * `excecao_encadeada` -- `caused_by` na ordem, e `matched_on: caused_by`: a
    classe que importa mora na causa raiz, nao no `SparkException` que a
    embrulha.
  * `texto_sem_forma_de_stacktrace` -- recusa nomeada, e nenhuma excecao
    inventada.
  * `reason_redigida` -- a redacao vem antes do parse, e o parse nao a desfaz.
  * `classe_no_meio_da_linha` -- o LIMITE atual: classe depois do prefixo do
    `DAGScheduler` sai como `sem_forma_de_stacktrace`, porque `_CABECA` e
    ancorada em `^`. Registra o comportamento de hoje, nao o desejado.
  * `nosuchmethod_com_jar_e_terraform` / `nosuchmethod_sem_jar` -- o PAR de
    SF-ERR-001. Mesmo event log, mesmo `main.tf`, um `.jar` a menos.
  * `nosuchfield_com_user_jars_first` -- SF-ERR-002, com `--user-jars-first`
    ligado e um jar cujo nome NAO encodifica Scala.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.errors.matcher import build_signature_matches
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.exception import EMITTED_KINDS as EXCEPTION_KINDS
from sparkforge.facts.exception import build_exceptions
from sparkforge.facts.migration import extract_migration_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "exception"

REQUIRED_FIXTURES = {
    "excecao_simples",
    "excecao_encadeada",
    "texto_sem_forma_de_stacktrace",
    "reason_redigida",
    "classe_no_meio_da_linha",
    "nosuchmethod_com_jar_e_terraform",
    "nosuchmethod_sem_jar",
    "nosuchfield_com_user_jars_first",
    # As TRES de classpath (2026-09-09): mesma familia de `SF-ERR-001`, e o que
    # as separa e o que cada uma afirma -- classe que nunca esteve, classe que
    # estava na compilacao, e classe presente na versao errada.
    "classnotfound_com_jar",
    "noclassdef_com_jar",
    "abstractmethod_com_jar",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _derive(directory: Path):
    """Os facts de artefato, mais os dois degraus de derivacao pura.

    Byte a byte o que `scripts/regen_fixtures.py::regen_exception` faz. A
    duplicacao e deliberada e e a mesma de todos os `test_fixtures_golden_*`:
    o script GRAVA o golden e este modulo o CONFERE, e um dos dois lendo o
    outro apagaria a conferencia.
    """
    entrada = directory / "input"
    facts = []
    for jsonl in sorted(entrada.glob("*.jsonl")):
        facts.extend(extract_event_log_path(jsonl, repo_root=entrada))
    if any(entrada.rglob("*.jar")):
        facts.extend(extract_migration_tree(entrada, repo_root=entrada))
    if any(entrada.rglob("*.tf")):
        facts.extend(extract_terraform_tree(entrada, repo_root=entrada))
    facts.extend(build_exceptions(facts))
    facts.extend(build_signature_matches(facts))
    return facts


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _derive(directory)
    findings, skipped = judge(
        facts, load_catalog(), meta["runtime"], return_skipped=True
    )
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _fixture(nome: str) -> Path:
    return FIXTURES / nome


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio de fixtures
# vazio, o pytest 8.x invoca o callable sobre o sentinela interno NOTSET durante
# a coleta e aborta a sessao INTEIRA, nao so este arquivo. Mesma guarda de
# `test_fixtures_golden_migration.py`.
@pytest.mark.parametrize(
    "directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()]
)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        esperado = json.loads(
            (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in facts] == esperado

    def test_findings_match_golden(self, directory):
        _, _, achados, _ = run_fixture(directory)
        esperado = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in achados] == esperado

    def test_declared_rules_all_fire(self, directory):
        meta, _, achados, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in achados}) == sorted(
            meta.get("expects_rules", [])
        )

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, achados, _ = run_fixture(directory)
        fact_ids = {f.id for f in facts}
        for fato in facts:
            validate_fact(fato.to_dict())
        for achado in achados:
            validate_finding(achado.to_dict(), fact_ids=fact_ids)

    def test_derivation_is_deterministic(self, directory):
        primeiro = [f.to_dict() for f in _derive(directory)]
        segundo = [f.to_dict() for f in _derive(directory)]
        assert primeiro == segundo

    def test_no_two_facts_share_an_id(self, directory):
        _, facts, _, _ = run_fixture(directory)
        ids = [f.id for f in facts]
        assert len(ids) == len(set(ids))

    def test_toda_falha_produz_excecao_ou_recusa(self, directory):
        """A sentinela de `build_exceptions`, exercitada por fixture.

        Lista vazia so pode acontecer quando NAO HA falha nenhuma. Havendo
        `spark.stage.failure`, sai `spark.exception` ou sai
        `spark.exception.unresolved` -- e "esta falha nao trouxe excecao"
        precisa ser distinguivel de "ninguem perguntou".
        """
        _, facts, _, _ = run_fixture(directory)
        falhas = len(_by_kind(facts, "spark.stage.failure"))
        assert falhas == 1, "toda fixture deste corpus tem exatamente uma falha"
        cabecas = len(_by_kind(facts, "spark.exception"))
        recusas = len(_by_kind(facts, "spark.exception.unresolved"))
        assert cabecas + recusas == falhas


class TestAForma:
    def test_a_forma_canonica_separa_classe_de_mensagem(self):
        _, facts, _, _ = run_fixture(_fixture("excecao_simples"))
        excecao = _by_kind(facts, "spark.exception")[0]
        assert excecao.attrs["exception_class"] == "java.lang.IllegalArgumentException"
        assert excecao.attrs["message_head"].startswith("requirement failed:")
        assert excecao.attrs["is_chained"] is False
        assert excecao.attrs["caused_by"] == []

    def test_os_frames_saem_estruturados_e_na_ordem_da_pilha(self):
        _, facts, _, _ = run_fixture(_fixture("excecao_simples"))
        frames = sorted(
            _by_kind(facts, "spark.exception.frame"), key=lambda f: f.subject["frame"]
        )
        assert [f.attrs["method"] for f in frames] == ["require", "resolve", "col"]
        assert [f.attrs["line"] for f in frames] == [337, 281, 1420]
        assert all(isinstance(f.attrs["line"], int) for f in frames), (
            "`line` inteiro, nao string: o avaliador de `expr` do catalogo "
            "compara numero"
        )

    def test_excecao_sem_assinatura_conhecida_recusa_com_nome(self):
        """Zero matches e indistinguivel de "o matcher nao rodou" sem isto."""
        _, facts, _, _ = run_fixture(_fixture("excecao_simples"))
        assert _by_kind(facts, "error.signature_match") == []
        recusas = _by_kind(facts, "error.signature.unresolved")
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == "nenhuma_assinatura_casou"
        assert recusas[0].attrs["exception_class"] == "java.lang.IllegalArgumentException"


class TestACadeia:
    def test_caused_by_sai_na_ordem_do_texto(self):
        _, facts, _, _ = run_fixture(_fixture("excecao_encadeada"))
        excecao = _by_kind(facts, "spark.exception")[0]
        assert excecao.attrs["is_chained"] is True
        assert excecao.attrs["caused_by"] == [
            "java.lang.reflect.InvocationTargetException",
            "java.lang.NoSuchMethodError",
        ], "a ultima e a causa raiz; trocar a ordem troca qual excecao causou qual"

    def test_a_assinatura_entra_pela_causa_raiz_e_nao_pelo_topo(self):
        """O ponto inteiro do fixture: o topo e `SparkException`, que nao casa
        assinatura nenhuma. Um matcher que olhasse so `exception_class`
        devolveria `nenhuma_assinatura_casou` sobre a MESMA falha que
        `nosuchmethod_com_jar_e_terraform` casa."""
        _, facts, _, _ = run_fixture(_fixture("excecao_encadeada"))
        excecao = _by_kind(facts, "spark.exception")[0]
        assert excecao.attrs["exception_class"] == "org.apache.spark.SparkException"
        casados = _by_kind(facts, "error.signature_match")
        assert len(casados) == 1
        assert casados[0].attrs["signature_id"] == "ERR-GLUE-002"
        assert casados[0].attrs["matched_on"] == "caused_by"
        assert casados[0].attrs["matched_class"] == "java.lang.NoSuchMethodError"
        assert _by_kind(facts, "error.signature.unresolved") == []


class TestAsRecusas:
    def test_texto_sem_forma_nao_inventa_excecao(self):
        _, facts, _, _ = run_fixture(_fixture("texto_sem_forma_de_stacktrace"))
        recusas = _by_kind(facts, "spark.exception.unresolved")
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == "sem_forma_de_stacktrace"
        assert _by_kind(facts, "spark.exception") == []
        assert _by_kind(facts, "spark.exception.frame") == []

    def test_sem_excecao_o_matcher_nao_conta_o_ponto_cego_de_novo(self):
        """`build_signature_matches` itera sobre `spark.exception`, e nao ha
        nenhum. Contar aqui diria que duas coisas falharam onde falhou uma."""
        _, facts, _, _ = run_fixture(_fixture("texto_sem_forma_de_stacktrace"))
        assert _by_kind(facts, "error.signature.unresolved") == []
        assert _by_kind(facts, "error.signature_match") == []

    def test_a_redacao_vem_antes_do_parse_e_o_parse_nao_a_desfaz(self):
        _, facts, _, _ = run_fixture(_fixture("reason_redigida"))
        falha = _by_kind(facts, "spark.stage.failure")[0]
        assert falha.attrs["redacted"] is True
        assert "warehouse.internal" not in falha.attrs["reason"], (
            "a senha da URL nao pode sobreviver ao handoff commitado"
        )
        recusas = _by_kind(facts, "spark.exception.unresolved")
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == "reason_redigida"

    def test_as_duas_recusas_de_parse_tem_nomes_diferentes(self):
        """Sem a guarda de `redacted`, o parser rodaria sobre `<redigido>` --
        que tambem nao casa `_CABECA` -- e as duas fixtures produziriam
        `sem_forma_de_stacktrace`. A diferenca entre "nao havia forma" e
        "havia, e foi apagada" sumiria do handoff, e cada uma destrava uma
        coisa diferente."""
        _, redigida, _, _ = run_fixture(_fixture("reason_redigida"))
        _, sem_forma, _, _ = run_fixture(_fixture("texto_sem_forma_de_stacktrace"))
        assert (
            _by_kind(redigida, "spark.exception.unresolved")[0].attrs["reason"]
            != _by_kind(sem_forma, "spark.exception.unresolved")[0].attrs["reason"]
        )

    def test_classe_no_meio_da_linha_agora_e_alcancada_pelo_SEGUNDO_padrao(self):
        """O limite que esta fixture registrava CAIU em 2026-09-09, e o golden
        dela e o diff que a queda produziu -- exatamente o que o `proves`
        original prometia.

        `_CABECA` continua ancorada em `^`. Quem alcanca esta forma e
        `_CABECA_APOS_EXECUTOR`, com ancora propria no prefixo literal do
        `DAGScheduler` (`executor <algo>):`), e `attrs.parsed_by` diz por qual
        dos dois a excecao entrou."""
        _, facts, _, _ = run_fixture(_fixture("classe_no_meio_da_linha"))
        falha = _by_kind(facts, "spark.stage.failure")[0]
        assert "java.lang.OutOfMemoryError" in falha.attrs["reason"]
        excecoes = _by_kind(facts, "spark.exception")
        assert len(excecoes) == 1
        assert excecoes[0].attrs["exception_class"] == "java.lang.OutOfMemoryError"
        assert excecoes[0].attrs["parsed_by"] == "after_executor"
        assert _by_kind(facts, "spark.exception.unresolved") == []

    def test_estruturar_a_excecao_NAO_inventa_assinatura(self):
        """A outra metade da medida, e ela e o que separa alargar o parser de
        alargar a acusacao: `java.lang.OutOfMemoryError` nao casa NENHUMA das
        seis assinaturas de `knowledge/errors/`, entao o ponto cego continua
        nomeado em `error.signature.unresolved`."""
        _, facts, achados, _ = run_fixture(_fixture("classe_no_meio_da_linha"))
        assert _by_kind(facts, "error.signature_match") == []
        recusa = _by_kind(facts, "error.signature.unresolved")
        assert len(recusa) == 1
        assert recusa[0].attrs["reason"] == "nenhuma_assinatura_casou"
        assert [a.rule_id for a in achados if a.rule_id.startswith("SF-ERR")] == []

    def test_a_pilha_normal_continua_entrando_pelo_primeiro_padrao(self):
        """A precedencia, medida no corpus e nao so no teste de unidade."""
        _, facts, _, _ = run_fixture(_fixture("excecao_simples"))
        assert _by_kind(facts, "spark.exception")[0].attrs["parsed_by"] == (
            "head_of_line"
        )


class TestOParDeRequiresFacts:
    def test_o_positivo_dispara_em_p0_com_as_tres_evidencias(self):
        _, facts, achados, _ = run_fixture(
            _fixture("nosuchmethod_com_jar_e_terraform")
        )
        assert _by_kind(facts, "error.signature_match")[0].attrs["signature_id"] == (
            "ERR-GLUE-002"
        )
        jar = _by_kind(facts, "mig.jar_binary")[0]
        assert jar.attrs["scala_minor"] == 12
        assert isinstance(jar.attrs["scala_minor"], int), (
            "INTEIRO, nao string: `attrs.scala_minor < 13` compara numero"
        )
        assert any(
            f.attrs.get("key") == "glue_version" and f.attrs.get("block") == "root"
            for f in _by_kind(facts, "tf.attribute")
        )
        err = [a for a in achados if a.rule_id == "SF-ERR-001"]
        assert len(err) == 1
        assert err[0].severity == "P0"

    def test_o_negativo_nao_dispara_e_a_recusa_nomeia_o_fact_que_falta(self):
        """A UNICA diferenca entre as duas fixtures e o `.jar`."""
        _, facts, achados, pulados = run_fixture(_fixture("nosuchmethod_sem_jar"))
        assert _by_kind(facts, "mig.jar_binary") == []
        assert _by_kind(facts, "error.signature_match")[0].attrs["signature_id"] == (
            "ERR-GLUE-002"
        ), "a excecao continua casando; e a EVIDENCIA que falta, nao o match"
        assert "SF-ERR-001" not in {a.rule_id for a in achados}
        recusa = [p for p in pulados if p.get("rule_id") == "SF-ERR-001"]
        assert len(recusa) == 1
        assert recusa[0]["reason"] == "requires_facts"
        assert recusa[0]["missing"] == ["mig.jar_binary"]

    def test_o_contrafactual_e_o_par_das_duas_fixtures(self):
        """O mesmo event log e o mesmo `main.tf` nos dois lados. Se os dois
        conjuntos de achados fossem iguais, `requires_facts` nao estaria
        fazendo trabalho nenhum -- que era exatamente o defeito do caminho
        antigo do matcher, casando a palavra e afirmando 98% de confianca."""
        com = _fixture("nosuchmethod_com_jar_e_terraform")
        sem = _fixture("nosuchmethod_sem_jar")
        assert (com / "input" / "eventlog.jsonl").read_bytes() == (
            sem / "input" / "eventlog.jsonl"
        ).read_bytes()
        assert (com / "input" / "main.tf").read_bytes() == (
            sem / "input" / "main.tf"
        ).read_bytes()
        _, _, achados_com, _ = run_fixture(com)
        _, _, achados_sem, _ = run_fixture(sem)
        assert {a.rule_id for a in achados_com} - {a.rule_id for a in achados_sem} == {
            "SF-ERR-001",
            "SF-SPARK4-004",
        }
        assert {a.rule_id for a in achados_sem} == set()

    def test_a_confirmada_e_a_estrutural_disparam_juntas_e_nao_sao_duplicata(self):
        """`rules/catalog/errors.yaml` afirma isso em prosa; aqui vira medida.

        A estrutural (SF-SPARK4-004) le o ARTEFATO e diz que este JAR nao pode
        carregar neste runtime. A confirmada (SF-ERR-001) le a EXECUCAO e diz
        que ele nao carregou, neste run. Uma e migracao a planejar, a outra e
        run a reprocessar.
        """
        _, _, achados, _ = run_fixture(_fixture("nosuchmethod_com_jar_e_terraform"))
        ids = {a.rule_id for a in achados}
        assert {"SF-ERR-001", "SF-SPARK4-004"} <= ids
        catalogo = {r["id"]: r for r in load_catalog()}
        assert catalogo["SF-ERR-001"]["status"] == "confirmed"
        assert catalogo["SF-SPARK4-004"]["status"] == "structural"


class TestUserJarsFirst:
    def test_a_flag_e_condicao_da_regra_e_nao_nota_de_rodape(self):
        _, facts, achados, _ = run_fixture(
            _fixture("nosuchfield_com_user_jars_first")
        )
        assert _by_kind(facts, "error.signature_match")[0].attrs["signature_id"] == (
            "ERR-GLUE-003"
        )
        assert any(
            f.attrs.get("key") == "--user-jars-first"
            and f.attrs.get("value") == "true"
            and f.attrs.get("block") == "default_arguments"
            for f in _by_kind(facts, "tf.attribute")
        )
        err = [a for a in achados if a.rule_id == "SF-ERR-002"]
        assert len(err) == 1
        assert err[0].severity == "P0"

    def test_jar_sem_scala_no_nome_fica_sem_a_chave_e_a_regra_de_piso_emudece(self):
        """Fail-closed de `_jar_facts`: um jar que nao declara Scala no nome
        pode ser Java puro, e inventar `0` faria SF-SPARK4-004 acusar em P0 um
        artefato que nunca teve versao de Scala nenhuma para estar errada. O
        runtime aqui e Glue 6.0 / Spark 4.0, dentro do escopo dela -- e mesmo
        assim ela nao dispara."""
        _, facts, achados, _ = run_fixture(
            _fixture("nosuchfield_com_user_jars_first")
        )
        jar = _by_kind(facts, "mig.jar_binary")[0]
        assert jar.attrs["scala"] == ""
        assert "scala_minor" not in jar.attrs
        assert {a.rule_id for a in achados} == {"SF-ERR-002"}


class TestAdversarial:
    def test_todo_kind_de_excecao_aparece_neste_corpus(self):
        """Recorte local do invariante global de
        `test_fixtures_kind_coverage.py`. Aqui ele falha com a mensagem certa:
        kind de excecao sem fixture de excecao."""
        vistos: set[str] = set()
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            vistos.update(f.kind for f in facts)
        assert set(EXCEPTION_KINDS) - vistos == set()

    def test_os_dois_kinds_do_matcher_aparecem_neste_corpus(self):
        from sparkforge.errors.matcher import EMITTED_KINDS as MATCHER_KINDS

        vistos: set[str] = set()
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            vistos.update(f.kind for f in facts)
        assert set(MATCHER_KINDS) - vistos == set()

    def test_as_duas_regras_da_area_disparam_neste_corpus(self):
        disparadas: set[str] = set()
        for directory in fixture_dirs():
            _, _, achados, _ = run_fixture(directory)
            disparadas.update(a.rule_id for a in achados)
        assert {"SF-ERR-001", "SF-ERR-002"} <= disparadas

    def test_nenhuma_derivacao_le_artefato(self):
        """As duas funcoes sao PURAS sobre Facts. Rodadas sobre a lista vazia
        elas devolvem lista vazia -- e nao um erro de arquivo nao encontrado,
        que e o que aconteceria se alguma delas tivesse voltado a abrir o event
        log."""
        assert build_exceptions([]) == []
        assert build_signature_matches([]) == []
