"""Golden do corpus do FOOTER do Parquet: o que o rodape decide.

Arquivo dedicado, mesma razao dos demais `test_fixtures_golden_*.py`, e uma a
mais: `tests/test_fixtures_kind_coverage.py::test_every_fixture_domain_has_a_golden_module`
recusa corpus sem modulo golden, porque sem ele o `Artifact parity gate` do CI
(`scripts/verify_wheel.py`) nunca executa o corpus -- ele coleta por
`test_fixtures_*.py`. Corpus que existe e nao roda contra o wheel parece
cobertura e nao e.

## O que este corpus mede

`knowledge/storage/parquet-layout.md` §2 declara que estatistica min/max so
serve se os valores estiverem AGRUPADOS. Medido em 2026-09-09, antes desta
frente: ZERO kind `parquet.*` no motor, e as cinco regras de `SF-PQ` julgavam
por listagem S3 e por plano fisico -- nenhuma abria um arquivo.

## O corpus, por eixo

  * `ordenado_poda` x `espalhado_nao_poda` -- o par que sustenta a frente. MESMO
    numero de linhas, MESMO `row_group_size`, MESMOS valores; so a ORDEM muda.
    Se a medida reagisse a tamanho ou a contagem, os dois dariam igual.
  * `espalhado_com_filtro` -- o mesmo footer de `espalhado_nao_poda` mais a
    query. E o contrato de `requires_facts` medido com um arquivo: sem
    `sql.predicate`, `SF-PQ-008` e pulada.
  * `sem_estatistica` -- `SF-PQ-007` dispara e `SF-PQ-008` nao: a segunda
    precisa da estatistica que a primeira diz faltar.
  * `row_group_minusculo` -- `SF-PQ-006` pelo lado de baixo, e a fixture que o
    separa de `SF-PQ-001` (arquivo contra row group).
  * `codec_misto` -- `SF-PQ-009`, no escopo do PREFIXO e nao do arquivo.
  * `amostra_parcial` -- a amostragem declarada chegando ao fact.

## O `.parquet` binario NAO mora no corpus

O input e o artefato JSON que `collect parquet-footer` gravaria, gerado a partir
de Parquet REAL e committado so nessa forma -- binario num corpus de fixture e
irrevisavel em diff. Quem exercita pyarrow de ponta a ponta e
`tests/test_collect_parquet_footer.py`, que escreve e le Parquet de verdade e
pula inteiro quando a dependencia opcional falta.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.parquet_footer import EMITTED_KINDS, extract_parquet_footer
from sparkforge.facts.sql_literal import extract_sql_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "parquet_footer"

REQUIRED_FIXTURES = {
    "ordenado_poda",
    "espalhado_nao_poda",
    "espalhado_com_filtro",
    "sem_estatistica",
    "row_group_minusculo",
    "codec_misto",
    "amostra_parcial",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _derive(directory: Path):
    """Byte a byte o que `scripts/regen_fixtures.py::regen_parquet_footer` faz.

    A duplicacao e deliberada e e a mesma de todos os `test_fixtures_golden_*`:
    o script GRAVA o golden e este modulo o CONFERE, e um dos dois lendo o outro
    apagaria a conferencia.

    O `.sql` entra sob GUARDA DE EXISTENCIA, e e isso que faz o par
    `espalhado_nao_poda`/`espalhado_com_filtro` medir `requires_facts`.
    """
    entrada = directory / "input"
    facts = []
    for artefato in sorted(entrada.glob("*.json")):
        payload = json.loads(artefato.read_text(encoding="utf-8"))
        facts.extend(
            extract_parquet_footer(payload, artefato.relative_to(entrada).as_posix())
        )
    for consulta in sorted(entrada.glob("*.sql")):
        facts.extend(extract_sql_path(consulta, repo_root=entrada))
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


def _perfil(facts, coluna: str):
    alvo = [
        f
        for f in facts
        if f.kind == "parquet.column_profile" and f.attrs.get("column") == coluna
    ]
    assert alvo, f"a coluna {coluna} precisa render perfil"
    return alvo[0]


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
        _, _, findings, _ = run_fixture(directory)
        esperado = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == esperado

    def test_every_fact_validates(self, directory):
        _, facts, _, _ = run_fixture(directory)
        for fato in facts:
            validate_fact(fato.to_dict())

    def test_every_finding_validates(self, directory):
        _, _, findings, _ = run_fixture(directory)
        for achado in findings:
            validate_finding(achado.to_dict())

    def test_todo_kind_emitido_esta_declarado(self, directory):
        """Kind que sai do extrator e nao esta em `EMITTED_KINDS` some das duas
        varreduras do repositorio -- a de cobertura e a de fronteira."""
        _, facts, _, _ = run_fixture(directory)
        do_extrator = {
            f.kind for f in facts if f.provenance.get("extractor", "").startswith("parquet_footer")
        }
        assert do_extrator <= EMITTED_KINDS

    def test_todo_artefato_produz_o_censo(self, directory):
        """`parquet.footer_analyzed` sai SEMPRE, inclusive quando nao ha arquivo
        lido. Sem ele, `files_read: 0` nunca apareceria, e zero declarado e
        diferente de campo ausente."""
        _, facts, _, _ = run_fixture(directory)
        assert len(_by_kind(facts, "parquet.footer_analyzed")) == 1


class TestOParQueSustentaAFrente:
    """A medida do §2 do `knowledge/`, exercitada nos dois sentidos."""

    def test_ordenado_poda_e_espalhado_nao(self):
        _, ordenado, _, _ = run_fixture(_fixture("ordenado_poda"))
        _, espalhado, _, _ = run_fixture(_fixture("espalhado_nao_poda"))
        a = _perfil(ordenado, "id")
        b = _perfil(espalhado, "id")
        assert a.measures["avg_range_coverage"] < 0.4
        assert b.measures["avg_range_coverage"] > 0.9

    def test_o_par_difere_SO_pela_ordem(self):
        """Se a medida reagisse a tamanho ou a contagem, os dois dariam igual --
        e e por isso que o par prova ORDENACAO."""
        _, ordenado, _, _ = run_fixture(_fixture("ordenado_poda"))
        _, espalhado, _, _ = run_fixture(_fixture("espalhado_nao_poda"))
        a = _perfil(ordenado, "id")
        b = _perfil(espalhado, "id")
        assert a.measures["num_row_groups"] == b.measures["num_row_groups"]
        assert a.measures["min_max_coverage"] == b.measures["min_max_coverage"] == 1.0
        assert a.measures["stats_coverage"] == b.measures["stats_coverage"] == 1.0
        # `total_byte_size` do PERFIL nao entra na comparacao, e a razao e
        # medida: ele e o tamanho COMPRIMIDO da coluna, e dado ordenado comprime
        # melhor que dado espalhado (16 086 contra 16 103 bytes neste par). O
        # que precisa ser igual e o que o par existe para isolar -- contagem de
        # row groups e cobertura de estatistica --, e o tamanho do ROW GROUP,
        # que o corpus fixa em escala de producao para que `SF-PQ-006` nao
        # dispare aqui e afogue o achado de ordenacao.
        assert {
            f.measures["total_byte_size"]
            for f in _by_kind(ordenado, "parquet.row_group")
        } == {
            f.measures["total_byte_size"]
            for f in _by_kind(espalhado, "parquet.row_group")
        }

    def test_expected_row_groups_scanned_e_a_leitura_do_operador(self):
        _, espalhado, _, _ = run_fixture(_fixture("espalhado_nao_poda"))
        perfil = _perfil(espalhado, "id")
        assert perfil.measures["expected_row_groups_scanned"] > 2.5
        assert perfil.measures["num_row_groups"] == 3.0


class TestOContratoDeRequiresFacts:
    """O par que mede `requires_facts` com UM arquivo."""

    def test_sem_a_query_a_regra_e_pulada_com_o_que_falta_nomeado(self):
        _, _, achados, pulados = run_fixture(_fixture("espalhado_nao_poda"))
        assert "SF-PQ-008" not in {a.rule_id for a in achados}
        pulo = {p["rule_id"]: p for p in pulados}["SF-PQ-008"]
        assert pulo["reason"] == "requires_facts"
        assert pulo["missing"] == ["sql.predicate"]

    def test_com_a_query_a_mesma_cobertura_vira_achado(self):
        _, facts, achados, _ = run_fixture(_fixture("espalhado_com_filtro"))
        assert "SF-PQ-008" in {a.rule_id for a in achados}
        assert _by_kind(facts, "sql.predicate")

    def test_o_footer_dos_dois_e_o_MESMO(self):
        """A diferenca do par e UM arquivo, e nada mais: se o footer diferisse,
        o par mediria duas coisas ao mesmo tempo."""
        sem = json.loads(
            (_fixture("espalhado_nao_poda") / "input" / "footer.json").read_text(
                encoding="utf-8"
            )
        )
        com = json.loads(
            (_fixture("espalhado_com_filtro") / "input" / "footer.json").read_text(
                encoding="utf-8"
            )
        )
        # O `prefix` e o `path` diferem de proposito -- sao o endereco, nao o
        # footer. O que precisa ser identico e o rodape de cada row group.
        assert [a["row_groups"] for a in sem["files"]] == [
            a["row_groups"] for a in com["files"]
        ]


class TestAsDuasRegrasDeEstatisticaNuncaDisparamJuntas:
    def test_sem_estatistica_dispara_a_da_ausencia(self):
        _, _, achados, _ = run_fixture(_fixture("sem_estatistica"))
        ids = {a.rule_id for a in achados}
        assert "SF-PQ-007" in ids
        assert "SF-PQ-008" not in ids

    def test_e_a_medida_de_faixa_recusa_com_nome(self):
        """`SF-PQ-008` precisa da estatistica que `SF-PQ-007` diz faltar, e a
        recusa nomeia isso em vez de sair como cobertura zero."""
        _, facts, _, _ = run_fixture(_fixture("sem_estatistica"))
        razoes = {f.attrs["reason"] for f in _by_kind(facts, "parquet.unresolved")}
        assert "estatistica_incompleta" in razoes
        assert "avg_range_coverage" not in _perfil(facts, "id").measures


class TestOEscopoDeCadaRegra:
    def test_row_group_e_do_ARQUIVO_e_codec_do_PREFIXO(self):
        """`SF-PQ-006` le `parquet.row_group` (um por row group de um arquivo);
        `SF-PQ-009` le `parquet.footer_analyzed` (um por prefixo). Trocar os
        escopos faria a segunda nao enxergar divergencia entre arquivos."""
        _, _, minusculo, _ = run_fixture(_fixture("row_group_minusculo"))
        _, _, codec, _ = run_fixture(_fixture("codec_misto"))
        assert {a.rule_id for a in minusculo} == {"SF-PQ-006"}
        assert {a.rule_id for a in codec} == {"SF-PQ-009"}

    def test_os_codecs_do_prefixo_saem_no_censo(self):
        _, facts, _, _ = run_fixture(_fixture("codec_misto"))
        censo = _by_kind(facts, "parquet.footer_analyzed")[0]
        assert censo.measures["distinct_codecs"] == 2.0
        assert censo.attrs["codecs"] == ["GZIP", "SNAPPY"]


class TestAmostragemDeclarada:
    def test_o_censo_parcial_se_anuncia(self):
        """Um censo parcial que nao se anuncia como parcial e pior que censo
        nenhum: o operador leria a amostra como a tabela."""
        _, facts, _, _ = run_fixture(_fixture("amostra_parcial"))
        censo = _by_kind(facts, "parquet.footer_analyzed")[0]
        assert censo.attrs["partial"] is True
        assert censo.measures["files_read"] < censo.measures["files_seen"]
        assert censo.attrs["sampling"] == "first_n_by_name"

    def test_o_censo_completo_nao_se_declara_parcial(self):
        _, facts, _, _ = run_fixture(_fixture("ordenado_poda"))
        assert _by_kind(facts, "parquet.footer_analyzed")[0].attrs["partial"] is False


class TestNenhumaRegraAfirmaGanho:
    """Regra 13 do `CLAUDE.md`, varrida sobre os achados deste corpus."""

    def test_nenhum_achado_publica_economia_ou_ganho(self):
        # `confidence` NAO entra na lista, e a razao e que ele nao e o que a
        # regra 13 proibe: e campo estrutural de TODO `Finding` deste
        # repositorio (`high`/`medium`/`low`, derivado do `status` da regra), e
        # nao um score de quanto a mudanca vai render. O que a regra 13 fecha e
        # afirmar ECONOMIA -- "voce economizaria X" exige o custo do run que nao
        # aconteceu.
        proibidos = ("expected_gain", "economia", "savings", "speedup", "roi")
        for directory in fixture_dirs():
            _, _, achados, _ = run_fixture(directory)
            for achado in achados:
                texto = json.dumps(achado.to_dict(), ensure_ascii=False).lower()
                for palavra in proibidos:
                    assert palavra not in texto, (directory.name, achado.rule_id, palavra)
