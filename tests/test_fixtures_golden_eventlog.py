"""Golden test do corpus de fixtures de event log.

Arquivo dedicado, separado de `test_fixtures_golden.py`. Aquele modulo esta
fortemente acoplado ao corpus PySpark: `REQUIRED_FIXTURES` e um conjunto
fechado de nomes, e `run_fixture` chama `extract_tree`, que caminha um
diretorio inteiro em busca de `*.py`. Uma fixture de event log e um unico
arquivo `*.jsonl` (nao uma arvore de modulos Python) extraido por
`extract_event_log_path`, nao por `extract_tree`. Encaixar as duas fontes no
mesmo helper exigiria ramificar `run_fixture` por tipo de fixture ou afrouxar
`REQUIRED_FIXTURES` para um superconjunto -- em ambos os casos o teste PySpark
existente fica mais fraco para servir a um formato de entrada diferente.
Um arquivo irmao, mesma estrutura de asserts, preserva os dois testes
igualmente rigorosos sem acoplar os dois formatos de fixture.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "eventlog"

REQUIRED_FIXTURES = {"skewed_stage"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for jsonl in sorted(input_dir.glob("*.jsonl")):
        facts.extend(extract_event_log_path(jsonl, repo_root=input_dir))
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
    def test_malformed_line_reported_not_silently_dropped(self):
        _, facts, _, _ = run_fixture(FIXTURES / "skewed_stage")
        unresolved = [f for f in facts if f.kind == "spark.unresolved"]
        assert unresolved
        assert unresolved[0].attrs["reason"] == "malformed_json"

    def test_executor_lost_without_heap_oom_is_classified_as_container(self):
        _, facts, _, _ = run_fixture(FIXTURES / "skewed_stage")
        lost = [f for f in facts if f.kind == "spark.executor.lost"]
        assert lost
        assert lost[0].attrs["heap_oom_in_log"] is False
        assert "OutOfMemoryError" not in lost[0].attrs["reason"]

    def test_healthy_stage_has_no_duration_skew(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "skewed_stage")
        healthy = next(
            f
            for f in facts
            if f.kind == "spark.stage.task_duration"
            and f.subject["symbol"] == "stage_healthy_read"
        )
        ratio = healthy.measures["max_ms"] / healthy.measures["p50_ms"]
        assert ratio < 3.0

    def test_skipped_stage_has_zero_task_count(self):
        _, facts, _, _ = run_fixture(FIXTURES / "skewed_stage")
        skipped_stage = next(
            f
            for f in facts
            if f.kind == "spark.stage.task_count"
            and f.subject["symbol"] == "stage_skipped_cached"
        )
        assert skipped_stage.measures["task_count"] == 0
