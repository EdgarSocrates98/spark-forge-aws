"""Golden test do corpus de fixtures de SQL.

Arquivo dedicado, mesma razao de `test_fixtures_golden_eventlog.py`: uma
fixture de SQL e um unico arquivo `*.sql` sob `input/`, extraida com
`extract_sql_path` -- nao ha `extract_sql_tree` (mesma decisao de
`event_log.py`, que tambem so tem variante por-arquivo).
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.sql_literal import extract_sql_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "sql"

REQUIRED_FIXTURES = {"select_star", "limit_without_filter", "clean_query"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for sql_file in sorted(input_dir.glob("*.sql")):
        facts.extend(extract_sql_path(sql_file, repo_root=input_dir))
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
    def test_clean_query_produces_zero_findings(self):
        _, _, findings, _ = run_fixture(FIXTURES / "clean_query")
        assert findings == []

    def test_all_ath_rules_blocked_or_missing_facts(self):
        """Nenhuma das cinco SF-ATH-* pode disparar so com texto SQL nesta
        fase, SEM fusao: SF-ATH-001/002/005 exigem os facts `.enriched` (ou
        `catalog.table_schema`) que so `sparkforge/facts/fusion.py` produz, a
        partir de `catalog.table_schema` -- fixture nenhuma deste corpus roda
        fusao nem tem catalogo. As duas restantes (catalog.table_partitions,
        athena.workgroup) exigem fact kinds que nenhum extrator deste corpus
        produz. Ver `tests/test_facts_fusion.py::TestEndToEndProbes` para as
        tres disparando de fato, uma vez fundidas com catalogo."""
        for name in ("select_star", "limit_without_filter", "clean_query"):
            _, _, findings, _ = run_fixture(FIXTURES / name)
            assert not [f for f in findings if f.rule_id.startswith("SF-ATH-")]

    def test_select_star_reason_is_requires_facts_not_silent(self):
        """SF-ATH-001 deixou de ser `blocked_on` (fusion.py existe agora);
        sem fusao rodar sobre este fixture, falta o fact `sql.projection.enriched`,
        entao o motivo do skip passa a ser `requires_facts` -- ainda explicito,
        nunca silencioso."""
        _, _, _, skipped = run_fixture(FIXTURES / "select_star")
        entry = next(s for s in skipped if s["rule_id"] == "SF-ATH-001")
        assert entry["reason"] == "requires_facts"
        assert "sql.projection.enriched" in entry["missing"]

    def test_table_format_columnar_is_never_fabricated(self):
        _, facts, _, _ = run_fixture(FIXTURES / "select_star")
        projection = next(f for f in facts if f.kind == "sql.projection")
        assert projection.attrs["star"] is True
        assert projection.attrs["table_format_columnar"] is None
