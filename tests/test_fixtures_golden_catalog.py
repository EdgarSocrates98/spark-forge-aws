"""Golden test do corpus de fixtures do Glue Data Catalog.

Arquivo dedicado, mesma razao de `test_fixtures_golden_iceberg.py`: uma
fixture de catalogo e uma arvore de `*.json` sob `input/`, extraida por
`extract_catalog_schema_tree`.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.catalog_schema import extract_catalog_schema_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "catalog"

REQUIRED_FIXTURES = {"glue_table_schema"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    return extract_catalog_schema_tree(input_dir, repo_root=input_dir)


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
    def test_glue_table_schema_produces_zero_findings(self):
        _, _, findings, _ = run_fixture(FIXTURES / "glue_table_schema")
        assert findings == []

    def test_minimal_table_still_produces_a_schema_fact(self):
        """db.sem_dados so tem `name` -- tem que sobreviver e ainda virar
        catalog.table_schema, sem inventar colunas/particoes."""
        _, facts, _, _ = run_fixture(FIXTURES / "glue_table_schema")
        minimal = next(
            f
            for f in facts
            if f.kind == "catalog.table_schema" and f.attrs["table"] == "db.sem_dados"
        )
        assert minimal.attrs["storage_format"] is None
        assert minimal.attrs["columnar"] is None
        assert minimal.attrs["partition_keys"] == []
        assert "column_count" not in minimal.measures

    def test_csv_table_is_marked_non_columnar(self):
        _, facts, _, _ = run_fixture(FIXTURES / "glue_table_schema")
        csv_table = next(
            f
            for f in facts
            if f.kind == "catalog.table_schema" and f.attrs["table"] == "db.legado_csv"
        )
        assert csv_table.attrs["columnar"] is False

    def test_projection_enabled_table_suppresses_sf_ath_003(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "glue_table_schema")
        assert any(f.kind == "catalog.table_property.projection_enabled" for f in facts)
        assert "SF-ATH-003" not in {f.rule_id for f in findings}
