"""Golden do corpus de LOG do CloudWatch: a linha redigida, e o que ela casa.

Arquivo dedicado, mesma razao dos demais `test_fixtures_golden_*.py`: o golden
guarda os facts de `sparkforge/facts/cloudwatch_logs.py` e os de
`sparkforge/errors/matcher.py::build_signature_matches` pelo caminho de LOG --
o segundo caminho que o matcher passou a ter.

## O que este corpus mede, e por que ele nao cabe no de excecao

MEDIDO em 2026-09-09 sobre `knowledge/errors/`: das SEIS assinaturas, apenas
`NoSuchMethodError` (ERR-GLUE-002) e `NoSuchFieldError` (ERR-GLUE-003) sao nome
de classe. As outras QUATRO -- ERR-ATH-001, ERR-GLUE-001, ERR-ICE-001 e
ERR-LF-001 -- sao trecho de mensagem de log, e por `spark.exception` nunca
casavam: o event log so carrega a excecao DO STAGE.

`fixtures/exception/` prova o caminho da excecao; este prova o do log, e
`quatro_assinaturas_de_log` e a fixture onde as quatro casam de uma vez. Junta-
las num corpus so misturaria duas fontes de artefato (event log e
`filter_log_events`) sob um `regen_*` que teria de despachar por forma.

## O corpus, por eixo

  * `quatro_assinaturas_de_log` -- as QUATRO que so o log alcanca, num artefato
    so, com uma linha INFO no meio que nao casa nada e nao vira ponto cego.
  * `assinatura_de_classe_pelas_duas_portas` -- ERR-GLUE-002 pela linha de log:
    e por isso que `matched_on` existe.
  * `nenhuma_assinatura_no_log` -- a recusa AGREGADA, uma por (run, log group),
    com `lines_examined`.
  * `linha_com_credencial` -- a redacao acontece ANTES de o texto virar fact, e
    a linha nao-segredo ao lado impede que a redacao vire apagador.
  * `corte_declarado` -- `truncated` em `measures`, onde a regra o le.
  * `log_group_inexistente` / `sem_permissao` / `janela_vazia` /
    `sem_credencial` -- as QUATRO recusas nomeadas, e o teste que cobra que elas
    sejam distinguiveis entre si.

## O eixo do JULGAMENTO, acrescentado em 2026-09-09

As quatro assinaturas de mensagem ganharam regra (`SF-ERR-003` a `SF-ERR-006`),
e regra exige o COMPANHEIRO que a assinatura declara -- a linha casada nao
basta. Por isso este corpus deixou de ser so log: sete fixtures novas trazem o
dump Iceberg, o event log, o inventario de consumidores e o Terraform ao lado
do log, cada um sob guarda de existencia.

  * `athena_v3_confirmado_no_log` x `athena_v3_sem_inventario` -- SF-ERR-003, e
    o par difere pelo `consumers.yaml`.
  * `yarn_kill_nas_duas_fontes` x `yarn_kill_so_no_log` -- SF-ERR-004, e o par
    difere pelo event log.
  * `commit_conflict_com_snapshots` -- SF-ERR-005, sem par negativo proprio: o
    dump da tabela e o unico companheiro, e a fixture sem ele seria
    `nenhuma_assinatura_no_log` com outra linha.
  * `lf_negado_com_catalogo_de_outra_conta` x `lf_negado_sem_catalogo_declarado`
    -- SF-ERR-006, e o par difere por UMA linha do mesmo `main.tf`.

O log do CloudWatch e o dump Iceberg sao os dois `*.json`, e por isso as
fixtures novas usam pasta: `input/logs/` para o log, `input/iceberg/` para o
dump. Sem as pastas o comportamento e o de antes, e e assim que as nove
originais continuam valendo byte a byte.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.errors.matcher import build_signature_matches
from sparkforge.facts.cloudwatch_logs import EMITTED_KINDS as CW_LOG_KINDS
from sparkforge.facts.cloudwatch_logs import extract_cloudwatch_logs_tree
from sparkforge.facts.consumers import extract_consumers_path
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.iceberg_metadata import extract_iceberg_metadata_tree
from sparkforge.facts.pyspark_ast import extract_tree as extract_pyspark_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "cloudwatch_logs"

REQUIRED_FIXTURES = {
    "quatro_assinaturas_de_log",
    "assinatura_de_classe_pelas_duas_portas",
    "nenhuma_assinatura_no_log",
    "linha_com_credencial",
    "corte_declarado",
    "log_group_inexistente",
    "sem_permissao",
    "janela_vazia",
    "sem_credencial",
    # As sete do eixo de JULGAMENTO (2026-09-09), quatro positivas e tres
    # negativas. `commit_conflict_com_snapshots` e a unica sem par proprio, e o
    # motivo esta no cabecalho.
    "athena_v3_confirmado_no_log",
    "athena_v3_sem_inventario",
    "yarn_kill_nas_duas_fontes",
    "yarn_kill_so_no_log",
    "commit_conflict_com_snapshots",
    "lf_negado_com_catalogo_de_outra_conta",
    "lf_negado_sem_catalogo_declarado",
    # As tres de `service: spark` (2026-09-09) -- as primeiras assinaturas que
    # nao falam de servico da AWS nenhum.
    "fetch_failed_com_executor_perdido",
    "fetch_failed_so_no_log",
    "python_worker_morreu_com_udf",
}

# As QUATRO de `knowledge/errors/` que sao trecho de MENSAGEM e nao classe de
# excecao. Lista literal e nao derivada de proposito: derivar "quais assinaturas
# nao parecem classe Java" de uma heuristica seria um segundo parser inventado
# aqui para conferir o primeiro. Se uma assinatura nova entrar no catalogo, esta
# lista nao muda sozinha -- e e isso que faz o teste ser uma afirmacao.
SO_PELO_LOG = {"ERR-ATH-001", "ERR-GLUE-001", "ERR-ICE-001", "ERR-LF-001"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _derive(directory: Path):
    """O extrator de artefato, os companheiros sob guarda, e a derivacao pura.

    Byte a byte o que `scripts/regen_fixtures.py::regen_cloudwatch_logs` faz. A
    duplicacao e deliberada e e a mesma de todos os `test_fixtures_golden_*`: o
    script GRAVA o golden e este modulo o CONFERE, e um dos dois lendo o outro
    apagaria a conferencia.

    Os companheiros entram sob guarda de EXISTENCIA, e e isso que faz o par
    positivo/negativo medir `requires_facts`: a fixture sem o arquivo produz o
    case sem o fact, e o motor pula a regra nomeando o que falta.
    """
    entrada = directory / "input"
    logs = entrada / "logs"
    facts = extract_cloudwatch_logs_tree(
        logs if logs.is_dir() else entrada, repo_root=entrada
    )
    for jsonl in sorted(entrada.glob("*.jsonl")):
        facts.extend(extract_event_log_path(jsonl, repo_root=entrada))
    if any(entrada.rglob("*.tf")):
        facts.extend(extract_terraform_tree(entrada, repo_root=entrada))
    iceberg = entrada / "iceberg"
    if iceberg.is_dir():
        facts.extend(extract_iceberg_metadata_tree(iceberg, repo_root=entrada))
    for inventario in sorted(entrada.glob("*.yaml")):
        facts.extend(extract_consumers_path(inventario, repo_root=entrada))
    if any(entrada.glob("*.py")):
        facts.extend(extract_pyspark_tree(entrada, repo_root=entrada))
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
# a coleta e aborta a sessao INTEIRA, nao so este arquivo.
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

    def test_todo_artefato_produz_o_analyzed(self, directory):
        """`cloudwatch.logs.analyzed` sai SEMPRE, inclusive nas quatro recusas.

        Sem ele, um artefato de recusa produziria so o `unresolved`, e o
        contador de linhas examinadas -- zero -- nunca apareceria. Zero
        declarado e diferente de campo ausente."""
        _, facts, _, _ = run_fixture(directory)
        assert len(_by_kind(facts, "cloudwatch.logs.analyzed")) == 1

    def test_nenhuma_linha_crua_de_segredo_atravessa_o_fact(self, directory):
        """A amarra da redacao, cobrada em TODO o corpus e nao so na fixture que
        a exercita. `facts.json` e committado como barramento de handoff."""
        _, facts, _, _ = run_fixture(directory)
        for fato in _by_kind(facts, "cloudwatch.log_event"):
            if fato.attrs.get("redacted"):
                assert fato.attrs["message"] == "<redigido>"


class TestAsQuatroQueSoOLogAlcanca:
    """O ponto da entrega inteira, medido em vez de afirmado."""

    def test_as_quatro_assinaturas_de_mensagem_casam_pelo_log(self):
        _, facts, _, _ = run_fixture(_fixture("quatro_assinaturas_de_log"))
        casados = {
            f.attrs["signature_id"] for f in _by_kind(facts, "error.signature_match")
        }
        assert casados == SO_PELO_LOG

    def test_todas_elas_entram_por_log_line_e_nao_por_classe(self):
        _, facts, _, _ = run_fixture(_fixture("quatro_assinaturas_de_log"))
        onde = {f.attrs["matched_on"] for f in _by_kind(facts, "error.signature_match")}
        assert onde == {"log_line"}

    def test_nenhuma_delas_casaria_pelo_caminho_da_excecao(self):
        """O contrafactual que da sentido ao teste acima: as quatro nao sao nome
        de classe, entao `build_signature_matches` sobre `spark.exception`
        nunca as alcanca. Sem esta assercao, "o log destrava quatro" seria
        afirmacao sobre um caminho que ninguem mediu."""
        from sparkforge.errors.matcher import DeterministicErrorMatcher
        from sparkforge.findings.models import Fact

        assinaturas = {
            s["id"]: s["signature"] for s in DeterministicErrorMatcher().signatures
        }
        for sig_id in SO_PELO_LOG:
            # A propria assinatura, posta no lugar da classe da excecao. Se ela
            # fosse nome de classe, casaria aqui -- e nao casa, porque uma
            # excecao real nunca tem "Cannot read unsupported version 3" no
            # `exception_class`. O que se mede e o caminho: mesmo COM o texto
            # ali, o par (classe, assinatura) so casa para as duas de classe.
            falso = Fact(
                kind="spark.exception",
                subject={"type": "stage", "stage_id": 1},
                attrs={
                    "exception_class": "org.apache.spark.SparkException",
                    "caused_by": [],
                },
                provenance={},
            )
            casados = [
                f
                for f in build_signature_matches([falso])
                if f.kind == "error.signature_match"
                and f.attrs["signature_id"] == sig_id
            ]
            assert not casados, (sig_id, assinaturas[sig_id])

    def test_a_linha_INFO_nao_vira_ponto_cego(self):
        """Recusa AGREGADA: um log com um match nao produz um `unresolved` por
        linha que nao casou."""
        _, facts, _, _ = run_fixture(_fixture("quatro_assinaturas_de_log"))
        assert len(_by_kind(facts, "cloudwatch.log_event")) == 5
        assert _by_kind(facts, "error.signature.unresolved") == []


class TestOMatchedOnDizPorOndeEntrou:
    def test_assinatura_de_classe_tambem_casa_pela_linha(self):
        _, facts, _, _ = run_fixture(
            _fixture("assinatura_de_classe_pelas_duas_portas")
        )
        casados = _by_kind(facts, "error.signature_match")
        assert [f.attrs["signature_id"] for f in casados] == ["ERR-GLUE-002"]
        assert casados[0].attrs["matched_on"] == "log_line"
        assert "NoSuchMethodError" in casados[0].attrs["matched_line"]


class TestARecusaAgregada:
    def test_log_sem_assinatura_conhecida_recusa_UMA_vez(self):
        _, facts, _, _ = run_fixture(_fixture("nenhuma_assinatura_no_log"))
        recusas = _by_kind(facts, "error.signature.unresolved")
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == "nenhuma_assinatura_casou_no_log"
        assert recusas[0].attrs["source"] == "cloudwatch.log_event"
        assert recusas[0].measures["lines_examined"] == 3.0

    def test_a_recusa_nao_carrega_o_indice_da_linha(self):
        """O ponto cego e do log inteiro, nao da linha 37."""
        _, facts, _, _ = run_fixture(_fixture("nenhuma_assinatura_no_log"))
        recusa = _by_kind(facts, "error.signature.unresolved")[0]
        assert "event" not in recusa.subject


class TestARedacaoVemAntesDoFact:
    def test_a_linha_com_senha_em_url_sai_redigida(self):
        _, facts, _, _ = run_fixture(_fixture("linha_com_credencial"))
        linhas = sorted(
            _by_kind(facts, "cloudwatch.log_event"), key=lambda f: f.subject["event"]
        )
        assert linhas[0].attrs["message"] == "<redigido>"
        assert linhas[0].attrs["redacted"] is True

    def test_a_linha_que_nao_e_segredo_sai_INTEIRA(self):
        """O par que impede a redacao de virar apagador: uma fixture so com a
        linha redigida passaria igual se `redact` redigisse tudo."""
        _, facts, _, _ = run_fixture(_fixture("linha_com_credencial"))
        linhas = sorted(
            _by_kind(facts, "cloudwatch.log_event"), key=lambda f: f.subject["event"]
        )
        assert "redacted" not in linhas[1].attrs
        assert "Container killed by YARN" in linhas[1].attrs["message"]

    def test_a_linha_redigida_nao_casa_assinatura_e_ainda_assim_e_contada(self):
        _, facts, _, _ = run_fixture(_fixture("linha_com_credencial"))
        casados = _by_kind(facts, "error.signature_match")
        assert [f.subject["event"] for f in casados] == [1]
        analisado = _by_kind(facts, "cloudwatch.logs.analyzed")[0]
        assert analisado.measures["events"] == 2.0
        assert analisado.measures["events_redacted"] == 1.0


class TestOCorteSeDeclara:
    def test_truncated_e_MEDIDA_e_nao_anotacao(self):
        """Ponto cego que so aparece em `attrs` some do julgamento: o avaliador
        de `expr` do catalogo compara numero."""
        _, facts, _, _ = run_fixture(_fixture("corte_declarado"))
        analisado = _by_kind(facts, "cloudwatch.logs.analyzed")[0]
        assert analisado.measures["truncated"] == 1.0
        assert analisado.measures["max_events"] == 2.0

    def test_o_corpus_tem_o_par_negativo(self):
        """Sem uma fixture com `truncated: 0`, o teste acima passaria mesmo se o
        extrator gravasse 1.0 sempre."""
        _, facts, _, _ = run_fixture(_fixture("quatro_assinaturas_de_log"))
        analisado = _by_kind(facts, "cloudwatch.logs.analyzed")[0]
        assert analisado.measures["truncated"] == 0.0


class TestAsQuatroRecusasNomeadas:
    RECUSAS = {
        "log_group_inexistente": "log_group_inexistente",
        "sem_permissao": "sem_permissao",
        "janela_vazia": "vazio",
        "sem_credencial": "sem_credencial",
    }

    @pytest.mark.parametrize("fixture,razao", sorted(RECUSAS.items()))
    def test_cada_recusa_nomeia_a_propria_razao(self, fixture, razao):
        _, facts, _, _ = run_fixture(_fixture(fixture))
        recusas = _by_kind(facts, "cloudwatch.logs.unresolved")
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == razao
        assert recusas[0].attrs["detail"], "recusa sem remedio e recusa muda"

    def test_as_quatro_sao_DISTINGUIVEIS_entre_si(self):
        """O invariante que da sentido aos quatro testes acima: as quatro
        produzem a MESMA lista vazia de eventos, e se duas colapsassem na mesma
        razao a recusa nomeada nao nomearia nada."""
        vistas = set()
        for fixture in self.RECUSAS:
            _, facts, _, _ = run_fixture(_fixture(fixture))
            vistas.add(_by_kind(facts, "cloudwatch.logs.unresolved")[0].attrs["reason"])
        assert len(vistas) == 4, vistas

    def test_recusa_nao_produz_linha_nenhuma(self):
        for fixture in self.RECUSAS:
            _, facts, _, _ = run_fixture(_fixture(fixture))
            assert _by_kind(facts, "cloudwatch.log_event") == [], fixture


def test_o_corpus_cobre_todo_kind_do_extrator():
    """A guarda local de `tests/test_fixtures_kind_coverage.py`, aqui tambem:
    ela conta o corpus INTEIRO, e este arquivo e quem responde por estes tres."""
    cobertos: set[str] = set()
    for directory in fixture_dirs():
        _, facts, _, _ = run_fixture(directory)
        cobertos |= {f.kind for f in facts}
    assert set(CW_LOG_KINDS) <= cobertos, sorted(set(CW_LOG_KINDS) - cobertos)
