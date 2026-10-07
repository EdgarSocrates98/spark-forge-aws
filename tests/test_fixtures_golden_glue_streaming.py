from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge_aws.facts.glue_streaming import extract_glue_streaming_tree
from sparkforge_aws.findings.models import sort_facts
from sparkforge_aws.findings.validate import validate_fact, validate_finding
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "glue_streaming"
REQUIRED_FIXTURES = {"rtm_valid", "rtm_missing_capacity", "rtm_incompatible"}


def fixture_dirs():
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = sort_facts(
        extract_glue_streaming_tree(directory / "input", repo_root=directory / "input")
    )
    return meta, facts, judge(facts, load_catalog(), {})


def test_glue_streaming_fixture_corpus_is_complete():
    assert {path.name for path in fixture_dirs()} == REQUIRED_FIXTURES
    for directory in fixture_dirs():
        meta, facts, findings = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        expected_findings = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [fact.to_dict() for fact in facts] == expected
        assert [finding.to_dict() for finding in findings] == expected_findings
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda path: path.name)
def test_glue_streaming_extraction_is_deterministic(directory: Path):
    first = run_fixture(directory)[1]
    second = run_fixture(directory)[1]
    assert [fact.to_dict() for fact in first] == [fact.to_dict() for fact in second]
