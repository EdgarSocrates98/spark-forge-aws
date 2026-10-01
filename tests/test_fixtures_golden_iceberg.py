"""Golden test do corpus de fixtures de metadata Iceberg.

Arquivo dedicado, mesma razao de `test_fixtures_golden_terraform.py` ser
separado do corpus PySpark: uma fixture Iceberg e uma arvore de `*.json` sob
`input/`, extraida por `extract_iceberg_metadata_tree`.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.iceberg_metadata import extract_iceberg_metadata_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "iceberg"

REQUIRED_FIXTURES = {
    "small_files",
    # O par de `small_files` nos ramos de `severity_by` de SF-ICE-001: media no
    # limiar EXATO de 8 MiB, onde o `<` do primeiro ramo decide. Sem ele o ramo
    # P2 nao aparecia em golden nenhum, e trocar aquele `<` por `<=` nao
    # quebrava nada.
    "small_files_at_p1_boundary",
    "delete_debt",
    "snapshot_churn",
    "healthy_table",
    "sort_order_debt",
    "sort_order_rewritten",
    "sort_order_unknown",
    "metadata_tables_full",
    # O trio de versao de spec, e a recusa. Ate 2026-09-02 o corpus era 9 de 9
    # em v2: o eixo de `format_version` nunca fora exercitado, e um kind que so
    # ve um valor em todo o corpus nao esta sendo testado.
    #
    # `format_v1_valida` tambem cobre a AUSENCIA da propriedade -- ali
    # `attrs.diverges` nao sai de todo, e a diferenca para `format_v3_com_
    # propriedade` (onde ele sai `false`) e o que prova que ausencia de lado nao
    # e concordancia.
    "format_v1_valida",
    "format_v3_com_propriedade",
    "format_version_diverge_da_propriedade",
    "format_version_ausente_no_dump",
    # O censo por `content`: os TRES estados no mesmo dump -- position,
    # equality, e a coluna ausente. Sem ela o eixo nao existia: os dois tipos
    # entravam no mesmo `delete_file_count`.
    "delete_content_separado",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    return extract_iceberg_metadata_tree(input_dir, repo_root=input_dir)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second


class TestAdversarial:
    def test_healthy_table_produces_zero_findings(self):
        _, _, findings, _ = run_fixture(FIXTURES / "healthy_table")
        assert findings == []

    def test_ice_004_nao_dispara_sem_sort_order_id_no_dump(self):
        """`small_files` tem sort order definido e nenhum `sort_order_id` nos
        data files -- e nem `default_sort_order_id`. Antes isso aparecia como
        `blocked_on`; hoje a regra e avaliavel, e o que a protege e o extrator
        nao emitir o atributo sem evidencia. Um dump velho, coletado antes da
        coluna existir, nao pode virar finding."""
        _, facts, findings, skipped = run_fixture(FIXTURES / "small_files")
        assert not [s for s in skipped if s["rule_id"] == "SF-ICE-004"]
        summary = next(f for f in facts if f.kind == "iceberg.files_summary")
        assert "written_before_sort_order" not in summary.attrs
        assert "SF-ICE-004" not in {f.rule_id for f in findings}

    def test_ice_004_dispara_e_mede_so_os_arquivos_anteriores(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "sort_order_debt")
        finding = next(f for f in findings if f.rule_id == "SF-ICE-004")
        summary = next(f for f in facts if f.kind == "iceberg.files_summary")
        assert summary.attrs["written_before_sort_order"] is True
        # 4 sob a ordem registrada anterior (piso confirmado), 2 sob a vigente,
        # 1 com sort_order_id 0 que continua sem resposta.
        assert summary.measures["files_written_before_sort_order"] == 4
        assert summary.measures["files_current_sort_order"] == 2
        assert summary.measures["files_sort_order_unknown"] == 1
        assert summary.measures["data_file_count"] == 7
        assert summary.id in finding.evidence

    def test_ice_004_nao_dispara_depois_do_rewrite(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "sort_order_rewritten")
        summary = next(f for f in facts if f.kind == "iceberg.files_summary")
        assert summary.attrs["written_before_sort_order"] is False
        assert findings == []

    def test_ice_004_trata_sort_order_id_zero_como_ponto_cego(self):
        """O caso Glue tipico: todo arquivo com `sort_order_id` 0 ou ausente,
        porque `SparkWrite` so passou a gravar o campo no Iceberg 1.11.0. A
        regra fica calada -- mas o dump precisa dizer que nao deu para olhar,
        nao que esta tudo bem."""
        _, facts, findings, _ = run_fixture(FIXTURES / "sort_order_unknown")
        summary = next(f for f in facts if f.kind == "iceberg.files_summary")
        assert "written_before_sort_order" not in summary.attrs
        assert summary.measures["files_sort_order_unknown"] == 4
        assert findings == []
        unresolved = [f for f in facts if f.kind == "iceberg.unresolved"]
        assert [u.attrs["reason"] for u in unresolved] == ["sort_order_id_missing"]
        analyzed = next(f for f in facts if f.kind == "iceberg.table_analyzed")
        assert analyzed.measures["unresolved_count"] == 1

    def test_both_severity_branches_of_the_small_files_rule_have_a_fixture(self):
        """Os dois ramos de SF-ICE-001, e o limiar que os separa.

        `small_files` tem 4 MB de media e cai no primeiro ramo;
        `small_files_at_p1_boundary` tem a media no limiar EXATO daquele ramo e
        cai no segundo. O `when` da regra casa nos dois -- as duas medias estao
        abaixo dos 32 MB do `threshold` --, entao o que separa as severidades e
        so a comparacao do ramo, e ela e `<`.

        Antes do segundo fixture o ramo P2 nao aparecia em golden nenhum: a
        severidade dele podia virar qualquer valor com a suite inteira verde, e
        trocar aquele `<` por `<=` nao quebrava nada, porque 4 MB esta longe
        demais do limiar para as duas comparacoes discordarem.

        Os numeros vem do CATALOGO, nunca repetidos aqui: um limiar escrito em
        dois lugares vira dois limiares no dia em que alguem ajustar so um.
        """
        regra = next(r for r in load_catalog() if r["id"] == "SF-ICE-001")
        agudo, moderado = regra["severity_by"]
        limiar_do_ramo = int(agudo["when"].rsplit("<", 1)[1])

        _, abaixo, findings_abaixo, _ = run_fixture(FIXTURES / "small_files")
        _, no_limiar, findings_no_limiar, _ = run_fixture(
            FIXTURES / "small_files_at_p1_boundary"
        )

        sumario_abaixo = next(f for f in abaixo if f.kind == "iceberg.files_summary")
        sumario_no_limiar = next(f for f in no_limiar if f.kind == "iceberg.files_summary")
        assert sumario_abaixo.measures["avg_file_bytes"] < limiar_do_ramo
        assert sumario_no_limiar.measures["avg_file_bytes"] == limiar_do_ramo
        # As duas continuam casando o `when`, senao o par nao provaria o ramo.
        assert sumario_no_limiar.measures["avg_file_bytes"] < regra["threshold"]["min_avg_bytes"]

        achado_abaixo = next(f for f in findings_abaixo if f.rule_id == "SF-ICE-001")
        achado_no_limiar = next(f for f in findings_no_limiar if f.rule_id == "SF-ICE-001")
        assert achado_abaixo.severity == agudo["severity"]
        assert achado_no_limiar.severity == moderado["severity"]

    def test_delete_debt_ratio_lives_on_one_fact(self):
        """SF-ICE-002 divide delete_file_count / data_file_count dentro de uma
        unica `expr`, avaliada contra o contexto de um so fact -- os dois
        precisam estar nas mesmas `measures`."""
        _, facts, _, _ = run_fixture(FIXTURES / "delete_debt")
        summary = next(f for f in facts if f.kind == "iceberg.delete_files_summary")
        assert summary.measures["delete_file_count"] == 10
        assert summary.measures["data_file_count"] == 50

    def test_small_files_sort_order_property_present_sem_evidencia_por_arquivo(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "small_files")
        sort_order = next(
            f
            for f in facts
            if f.kind == "iceberg.table_property" and f.attrs.get("key") == "sort-order"
        )
        assert sort_order.attrs["present"] is True
        assert "SF-ICE-004" not in {f.rule_id for f in findings}

    def test_snapshot_churn_has_no_files_facts(self):
        """Dump so com `snapshots`: nao pode fabricar files/delete_files."""
        _, facts, _, _ = run_fixture(FIXTURES / "snapshot_churn")
        assert not [f for f in facts if f.kind == "iceberg.files_summary"]
        assert not [f for f in facts if f.kind == "iceberg.delete_files_summary"]
