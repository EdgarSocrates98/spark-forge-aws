"""Golden test do corpus de fixtures de plano fisico.

Arquivo dedicado, pela mesma razao de `test_fixtures_golden_eventlog.py` ser
separado de `test_fixtures_golden.py`: uma fixture de plano e um unico arquivo
de TEXTO (a saida colada de `explain`), extraido por `extract_plan_path`, nao
uma arvore de `*.py` varrida por `extract_tree`. Cada corpus novo ganha um
modulo irmao com a mesma estrutura de asserts em vez de afrouxar o corpus
existente.

O golden falha nos DOIS sentidos, de proposito: um achado que sumiu e um
achado inventado quebram o mesmo `assert`. `pruning_ok` existe so para provar
o segundo -- um plano com pruning funcionando e leitura estreita nao pode
produzir Finding nenhum.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "plan"

REQUIRED_FIXTURES = {
    "pruning_ok",
    "pruning_absent",
    "wide_read_schema",
    "truncated_plan",
    "iceberg_batch_scan",
    "python_udf_in_plan",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for plan in sorted(input_dir.glob("*.txt")):
        facts.extend(extract_plan_path(plan, repo_root=input_dir))
    return facts


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
    def test_working_pruning_produces_zero_findings(self):
        """Prova de que a regra nao acusa quem esta certo. Acusar configuracao
        correta destroi a confianca em todo o resto do relatorio, e SF-PQ-002 e
        P0: um falso positivo aqui manda o operador reescrever uma leitura que
        ja estava otima."""
        _, _, findings, _ = run_fixture(FIXTURES / "pruning_ok")
        assert findings == []

    def test_pruning_absent_is_anchored_to_the_scan_node(self):
        _, _, findings, _ = run_fixture(FIXTURES / "pruning_absent")
        finding = next(f for f in findings if f.rule_id == "SF-PQ-002")
        assert finding.subject["type"] == "plan_node"
        assert finding.subject["relation"] == "analytics.transacoes"
        assert finding.severity == "P0"

    def test_truncated_plan_reports_a_blind_spot_and_no_ratio_finding(self):
        """Uma lista de campos truncada infla o numerador de SF-PQ-004 em
        silencio. O golden exige as duas metades: o ponto cego contado, E
        nenhum finding derivado da contagem parcial."""
        _, facts, findings, _ = run_fixture(FIXTURES / "truncated_plan")
        reasons = {f.attrs.get("reason") for f in facts if f.kind == "plan.unresolved"}
        assert "truncated_field_list" in reasons
        assert [f.rule_id for f in findings] == []
        scan = next(f for f in facts if f.kind == "plan.file_scan")
        assert "read_schema_columns" not in scan.measures

    def test_iceberg_batch_scan_never_fires_partition_pruning(self):
        """`BatchScan` v2 nao tem a semantica de `PartitionFilters` de v1.
        Tratar os dois como iguais acusaria SF-PQ-002 em toda tabela Iceberg."""
        _, facts, findings, _ = run_fixture(FIXTURES / "iceberg_batch_scan")
        scan = next(f for f in facts if f.kind == "plan.file_scan")
        assert scan.attrs["scan_api"] == "v2_batch_scan"
        assert scan.attrs["partition_filters_empty"] == "unknown"
        assert "SF-PQ-002" not in {f.rule_id for f in findings}

    def test_wide_read_schema_fires_only_the_column_rule(self):
        _, _, findings, _ = run_fixture(FIXTURES / "wide_read_schema")
        assert {f.rule_id for f in findings} == {"SF-PQ-004"}

    def test_python_udf_nodes_keep_their_flavor(self):
        """`BatchEvalPython` e `ArrowEvalPython` nao sao a mesma coisa: a
        primeira serializa registro a registro para o interpretador Python, a
        segunda e vetorizada por Arrow. Colapsar as duas em "tem UDF" apaga a
        diferenca que decide se vale reescrever. Nenhuma regra consome
        `plan.python_udf` -- e justamente o fact sem regra que some numa
        refatoracao sem ninguem notar, entao ele tem golden."""
        _, facts, findings, _ = run_fixture(FIXTURES / "python_udf_in_plan")
        udfs = {
            f.attrs["operator"]: f.attrs["udf_type"] for f in facts if f.kind == "plan.python_udf"
        }
        assert udfs == {"BatchEvalPython": "python", "ArrowEvalPython": "pandas"}
        assert findings == []

    def test_unresolved_is_never_silently_zero_where_it_is_not(self):
        """`plan.analyzed` e a sentinela: prova que a extracao rodou. Sem ela,
        uma condicao `absent:` sobre fact de plano seria vacuamente verdadeira
        quando o extrator nunca rodou."""
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            sentinel = next(f for f in facts if f.kind == "plan.analyzed")
            counted = sum(1 for f in facts if f.kind == "plan.unresolved")
            assert sentinel.measures["unresolved_count"] == counted, directory.name
