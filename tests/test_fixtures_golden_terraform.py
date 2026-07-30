"""Golden test do corpus de fixtures de Terraform.

Arquivo dedicado, mesma razao de `test_fixtures_golden_eventlog.py` ser
separado de `test_fixtures_golden.py`: uma fixture de Terraform e uma arvore
de `*.tf` sob `input/`, extraida por `extract_terraform_tree`, nao por
`extract_tree` (que caminha `*.py`). Mesma estrutura de asserts, formato de
entrada diferente.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "terraform"

REQUIRED_FIXTURES = {"autoscaling_conflict", "no_observability", "secret_in_arguments", "clean_job"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    return extract_terraform_tree(input_dir, repo_root=input_dir)


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
    def test_clean_job_produces_zero_findings(self):
        _, _, findings, _ = run_fixture(FIXTURES / "clean_job")
        assert findings == []

    def test_secret_value_is_never_present_in_facts(self):
        """Nenhum golden pode carregar a credencial de exemplo em claro."""
        _, facts, _, _ = run_fixture(FIXTURES / "secret_in_arguments")
        secret = next(
            f
            for f in facts
            if f.kind == "tf.attribute" and f.attrs.get("secret_pattern_match") is True
        )
        assert secret.attrs["value"] == "<redigido>"
        assert "AKIA" not in json.dumps(secret.to_dict())

    def test_no_observability_fixture_has_no_spark_ui_sentinel(self):
        _, facts, _, _ = run_fixture(FIXTURES / "no_observability")
        assert not [f for f in facts if f.kind == "tf.observability.spark_ui"]
        assert [f for f in facts if f.kind == "tf.module_analyzed"]

    def test_autoscaling_conflict_evidence_covers_both_conditions(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "autoscaling_conflict")
        finding = next(f for f in findings if f.rule_id == "SF-GLUE-001")
        evidence_facts = [f for f in facts if f.id in finding.evidence]
        keys = {f.attrs.get("key") for f in evidence_facts}
        assert "--enable-auto-scaling" in keys
        assert "number_of_workers" in keys
