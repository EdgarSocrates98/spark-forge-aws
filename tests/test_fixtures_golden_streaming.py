"""Golden corpus da primeira onda de Structured Streaming.

O corpus separa código declarativo de progresso observado. Isso impede que uma
regra de execução seja provada por AST e mantém o caso de runtime divergente
visível no mesmo julgamento que a série.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.facts.streaming import extract_streaming_progress_tree
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming"

REQUIRED_FIXTURES = {
    "source_positive",
    "source_clean",
    "progress_positive",
    "progress_unresolved",
    "progress_runtime_divergent",
}


def fixture_dirs():
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    if meta["artifact"] == "source":
        facts = extract_tree(input_dir, repo_root=input_dir)
        runtime_file = directory / "runtime.json"
        if runtime_file.exists():
            context, runtime_facts = detect_runtime(
                json.loads(runtime_file.read_text(encoding="utf-8"))
            )
            facts.extend(runtime_facts)
            runtime = context.to_dict()
        else:
            runtime = meta["runtime"]
    else:
        facts = extract_streaming_progress_tree(input_dir, repo_root=input_dir)
        runtime_file = directory / "runtime.json"
        if runtime_file.exists():
            sources = json.loads(runtime_file.read_text(encoding="utf-8"))
            context, runtime_facts = detect_runtime(sources)
            facts.extend(runtime_facts)
            runtime = context.to_dict()
        else:
            runtime = meta["runtime"]
    facts = sort_facts(facts)
    findings, skipped = judge(facts, load_catalog(), runtime, return_skipped=True)
    return meta, facts, findings, skipped


def test_all_required_fixtures_exist():
    assert {path.name for path in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda path: path.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [fact.to_dict() for fact in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [finding.to_dict() for finding in findings] == expected

    def test_declared_kinds_and_rules_match(self, directory):
        meta, facts, findings, _ = run_fixture(directory)
        assert {fact.kind for fact in facts} == set(meta.get("expects_kinds", []))
        assert sorted({finding.rule_id for finding in findings}) == sorted(
            meta.get("expects_rules", [])
        )

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = run_fixture(directory)[1]
        second = run_fixture(directory)[1]
        assert [fact.to_dict() for fact in first] == [fact.to_dict() for fact in second]


class TestAdversarial:
    def test_source_fixture_exercises_every_static_streaming_kind(self):
        _, facts, _, _ = run_fixture(FIXTURES / "source_positive")
        kinds = {fact.kind for fact in facts}
        assert {
            "streaming.source",
            "streaming.sink",
            "streaming.checkpoint",
            "streaming.trigger",
            "streaming.output_mode",
            "streaming.watermark",
            "streaming.stateful_operation",
            "streaming.join",
            "streaming.dedup",
            "streaming.foreach_batch",
            "streaming.query",
            "streaming.module_analyzed",
        } <= kinds

    def test_clean_source_has_no_streaming_facts_or_findings(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "source_clean")
        assert not [fact for fact in facts if fact.kind.startswith("streaming.")]
        assert findings == []

    def test_insufficient_progress_never_becomes_a_trend(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "progress_unresolved")
        assert any(fact.kind == "streaming.progress.unresolved" for fact in facts)
        assert not any(fact.kind == "streaming.progress.series" for fact in facts)
        assert findings == []

    def test_runtime_divergence_is_preserved_alongside_streaming_findings(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "progress_runtime_divergent")
        runtime_signal = next(fact for fact in facts if fact.kind == "env.runtime_signal")
        assert runtime_signal.measures["distinct_versions"] == 2
        assert "SF-ENV-001" in {finding.rule_id for finding in findings}
        assert "SF-STREAM-002" in {finding.rule_id for finding in findings}
