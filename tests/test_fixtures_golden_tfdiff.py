"""Golden test do corpus tfdiff.

Corpus do diff de Terraform, que desbloqueou SF-GLUE-005.

`input/before/` e `input/after/` sao dois estados do mesmo modulo -- o
`main` e o branch do PR -- e `input/*.jsonl` e o event log do run. A
regra pergunta se alguem aumentou o worker SEM evidencia de pressao de
memoria, e isso exige as duas fontes: a mudanca vem do diff, a
evidencia vem do log.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.terraform import extract_terraform_diff
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "tfdiff"

REQUIRED_FIXTURES = {"worker_upsized_no_evidence", "worker_upsized_with_spill"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = list(
        extract_terraform_diff(
            input_dir / "before", input_dir / "after", repo_root=input_dir
        )
    )
    for log in sorted(input_dir.glob("*.jsonl")):
        facts.extend(extract_event_log_path(log, repo_root=input_dir))
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
        assert [f.to_dict() for f in _extract(directory)] == [
            f.to_dict() for f in _extract(directory)
        ]


class TestAdversarial:
    def test_upsize_without_evidence_fires(self):
        _, _, findings, _ = run_fixture(FIXTURES / "worker_upsized_no_evidence")
        assert "SF-GLUE-005" in {f.rule_id for f in findings}

    def test_upsize_with_spill_does_not_fire(self):
        """A metade que impede a regra de virar ruido em todo PR de
        infraestrutura: com spill, o worker maior esta justificado."""
        _, _, findings, _ = run_fixture(FIXTURES / "worker_upsized_with_spill")
        assert "SF-GLUE-005" not in {f.rule_id for f in findings}

    def test_the_changed_attribute_carries_the_previous_value(self):
        """Sem `previous_value` o achado diz "mudou" sem dizer de que para que,
        e o revisor tem que ir ao git para entender o proprio finding."""
        _, facts, _, _ = run_fixture(FIXTURES / "worker_upsized_no_evidence")
        worker = next(
            f for f in facts if f.kind == "tf.attribute" and f.attrs.get("key") == "worker_type"
        )
        assert worker.attrs["changed"] is True
        assert worker.attrs["previous_value"] == "G.1X"
        assert worker.attrs["value"] == "G.4X"

    def test_unchanged_attributes_are_marked_false_not_omitted(self):
        """`changed: false` explicito distingue "nao mudou" de "esta extracao
        nao sabe se mudou", que e o estado dos facts do extrator normal."""
        _, facts, _, _ = run_fixture(FIXTURES / "worker_upsized_no_evidence")
        unchanged = [
            f for f in facts if f.kind == "tf.attribute" and f.attrs.get("key") == "glue_version"
        ]
        assert unchanged and unchanged[0].attrs["changed"] is False

    def test_only_the_after_side_is_reported(self):
        """Devolver os dois lados faria toda regra contar cada recurso duas
        vezes -- e acusar o estado antigo, que ninguem pode mais consertar."""
        _, facts, _, _ = run_fixture(FIXTURES / "worker_upsized_no_evidence")
        resources = [f for f in facts if f.kind == "tf.resource"]
        assert len(resources) == 1

    def test_spill_summary_answers_at_the_job_level(self):
        """`spark.stage.spill` existe para todo stage, com zero inclusive --
        por isso a pergunta "o job derramou?" precisa do fact de job."""
        _, facts, _, _ = run_fixture(FIXTURES / "worker_upsized_with_spill")
        summary = next(f for f in facts if f.kind == "spark.job.spill_summary")
        assert summary.measures["stages_with_spill"] == 1
