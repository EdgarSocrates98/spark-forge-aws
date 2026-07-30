import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "pyspark"

REQUIRED_FIXTURES = {
    "python_udf",
    "collect_unbounded",
    "join_before_reduction",
    "action_in_loop",
    "coalesce_one",
    "explode_unbounded",
    "withcolumn_run",
    "cache_no_unpersist",
    "forced_broadcast",
    "repartition_literal",
    "dedup_no_columns",
    "conf_set_conflict",
    "dynamic_dispatch",
    "clean_job",
    "near_threshold",
    "version_out_of_scope",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
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

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in extract_tree(directory / "input", directory / "input")]
        second = [f.to_dict() for f in extract_tree(directory / "input", directory / "input")]
        assert first == second


class TestAdversarial:
    def test_clean_job_produces_zero_findings(self):
        _, _, findings, _ = run_fixture(FIXTURES / "clean_job")
        assert findings == []

    def test_dynamic_dispatch_reports_unresolved_and_no_findings(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "dynamic_dispatch")
        assert [f for f in facts if f.kind == "pyspark.unresolved"]
        assert findings == []

    def test_near_threshold_does_not_fire(self):
        """withColumn run_length = 9, limiar SF-PY-007 = 10."""
        _, facts, findings, _ = run_fixture(FIXTURES / "near_threshold")
        runs = [f for f in facts if f.kind == "pyspark.withcolumn_run"]
        assert runs and runs[0].measures["run_length"] == 9
        assert "SF-PY-007" not in {f.rule_id for f in findings}

    def test_out_of_scope_rule_is_reported_as_skipped_with_reason(self):
        _, _, findings, skipped = run_fixture(FIXTURES / "version_out_of_scope")
        by_version = [s for s in skipped if s["reason"] == "runtime_scope"]
        assert by_version, "nenhuma regra reportada como skipped por versao"
        assert "SF-ENV-002" in {s["rule_id"] for s in by_version}
