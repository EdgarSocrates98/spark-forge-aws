from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.flink import extract_flink_tree
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "flink"
REQUIRED_FIXTURES = {
    "flink_positive",
    "flink_checkpoint_failed",
    "flink_temporal_metrics",
    "flink_unresolved",
    "managed_positive",
    "managed_unresolved",
}


def fixture_dirs():
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = sort_facts(extract_flink_tree(directory / "input", artifact=meta["artifact"]))
    return meta, facts, judge(facts, load_catalog(), {})


def test_flink_fixture_corpus_is_complete():
    assert {path.name for path in fixture_dirs()} == REQUIRED_FIXTURES
    for directory in fixture_dirs():
        meta, facts, findings = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        expected_findings = json.loads((directory / "expected" / "findings.json").read_text(encoding="utf-8"))
        assert [fact.to_dict() for fact in facts] == expected
        assert [finding.to_dict() for finding in findings] == expected_findings
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda path: path.name)
def test_flink_extraction_is_deterministic(directory: Path):
    first = run_fixture(directory)[1]
    second = run_fixture(directory)[1]
    assert [fact.to_dict() for fact in first] == [fact.to_dict() for fact in second]
