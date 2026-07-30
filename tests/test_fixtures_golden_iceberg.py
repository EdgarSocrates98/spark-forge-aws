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

REQUIRED_FIXTURES = {"small_files", "delete_debt", "snapshot_churn", "healthy_table"}


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

    def test_ice_004_is_blocked_not_missing(self):
        """SF-ICE-004 nunca pode disparar (nenhum dump unico sabe se os data
        files existentes sao anteriores ao sort order). Isso precisa aparecer
        como `blocked_on` explicito em `skipped`, nao como silencio."""
        _, _, _, skipped = run_fixture(FIXTURES / "small_files")
        entry = next(s for s in skipped if s["rule_id"] == "SF-ICE-004")
        assert entry["reason"] == "blocked_on"

    def test_delete_debt_ratio_lives_on_one_fact(self):
        """SF-ICE-002 divide delete_file_count / data_file_count dentro de uma
        unica `expr`, avaliada contra o contexto de um so fact -- os dois
        precisam estar nas mesmas `measures`."""
        _, facts, _, _ = run_fixture(FIXTURES / "delete_debt")
        summary = next(f for f in facts if f.kind == "iceberg.delete_files_summary")
        assert summary.measures["delete_file_count"] == 10
        assert summary.measures["data_file_count"] == 50

    def test_small_files_sort_order_property_present_but_rule_blocked(self):
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
