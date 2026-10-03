from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.schema_registry import extract_schema_registry_tree
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "schema_registry"
REQUIRED_FIXTURES = {
    "schema_compatible",
    "schema_incompatible",
    "schema_unresolved",
    "schema_invalid",
}


def fixture_dirs():
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda path: path.name)
def test_schema_registry_fixture_goldens(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = sort_facts(
        extract_schema_registry_tree(directory / "input", repo_root=directory / "input")
    )
    findings = judge(facts, load_catalog(), {})
    assert [fact.to_dict() for fact in facts] == json.loads(
        (directory / "expected/facts.json").read_text(encoding="utf-8")
    )
    assert [finding.to_dict() for finding in findings] == json.loads(
        (directory / "expected/findings.json").read_text(encoding="utf-8")
    )
    assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
    for fact in facts:
        validate_fact(fact.to_dict())
    for finding in findings:
        validate_finding(finding.to_dict())


def test_schema_registry_fixture_corpus_is_complete():
    assert {path.name for path in fixture_dirs()} == REQUIRED_FIXTURES
