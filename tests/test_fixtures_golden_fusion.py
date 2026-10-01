"""Golden test do corpus de fixtures de fusao.

Uma fixture de fusao tem `*.sql` E `*.json` sob `input/` -- a query e o dump
de catalogo que ela precisa correlacionar. Extrai as duas fontes, roda
`fuse`, e SO ENTAO julga -- ver `scripts/regen_fixtures.py::regen_fusion`.
Este e o corpus que prova, ponta a ponta e via golden output versionado, que
SF-ATH-001/002/005 disparam (ou corretamente nao disparam) a partir de facts
fundidos de verdade.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.catalog_schema import extract_catalog_schema_path
from sparkforge.facts.fusion import fuse
from sparkforge.facts.sql_literal import extract_sql_path
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fusion"

REQUIRED_FIXTURES = {
    "select_star_parquet",
    "limit_no_filter_with_catalog",
    "limit_no_filter_multi_query",
    "limit_partition_filter_guard",
    "partition_type_mismatch",
    # A unica deste corpus com `.tf`: SF-ICE-008 correlaciona a OPERACAO do
    # texto SQL com a EXTENSAO declarada na configuracao, e nenhum dos dois
    # lados a conhece sozinho.
    "merge_sem_extensoes_do_iceberg",
    # A segunda deste corpus com `.tf`, e a que exige a versao EMBARCADA de
    # Iceberg -- derivada da `GLUE_MATRIX` a partir do `glue_version` que o
    # proprio Terraform declara.
    "iceberg_declarado_diferente_do_runtime",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for sql_file in sorted(input_dir.glob("*.sql")):
        facts.extend(extract_sql_path(sql_file, repo_root=input_dir))
    for json_file in sorted(input_dir.glob("*.json")):
        facts.extend(extract_catalog_schema_path(json_file, repo_root=input_dir))
    # `*.tf` sob GUARDA DE DIRETORIO, no mesmo molde do runner de
    # `cloudwatch_logs`: a fusao passou a resolver `sql.write_statement` contra a
    # configuracao da sessao, e configuracao chega pelas tres superficies -- a de
    # Terraform e a que este corpus consegue trazer sem acrescentar facts de
    # PySpark. Fixture sem `.tf` continua extraindo exatamente o que extraia.
    if any(input_dir.glob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
    return fuse(facts)


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

    def test_extraction_and_fusion_is_deterministic(self, directory):
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second

    def test_fuse_is_idempotent_in_fact_content(self, directory):
        once = _extract(directory)
        twice = fuse(once)
        key = lambda facts: sorted((f.to_dict() for f in facts), key=lambda d: (d["kind"], d["id"]))  # noqa: E731
        assert key(once) == key(twice)


class TestDecisiveProbes:
    """Cada fixture deste corpus e, por construcao, uma das provas decisivas
    pedidas: SF-ATH-001, SF-ATH-002 disparando, SF-ATH-002 NAO disparando com
    filtro de particao real (guarda contra falso positivo), e SF-ATH-005."""

    def test_sf_ath_001_fires(self):
        _, _, findings, _ = run_fixture(FIXTURES / "select_star_parquet")
        assert {f.rule_id for f in findings} == {"SF-ATH-001"}

    def test_sf_ath_002_fires_without_any_filter(self):
        _, _, findings, _ = run_fixture(FIXTURES / "limit_no_filter_with_catalog")
        assert {f.rule_id for f in findings} == {"SF-ATH-002"}

    def test_sf_ath_002_does_not_fire_with_real_partition_filter(self):
        _, _, findings, _ = run_fixture(FIXTURES / "limit_partition_filter_guard")
        assert findings == []

    def test_sf_ath_005_fires_on_type_mismatch(self):
        _, _, findings, _ = run_fixture(FIXTURES / "partition_type_mismatch")
        assert {f.rule_id for f in findings} == {"SF-ATH-005"}
