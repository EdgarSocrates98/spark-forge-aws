from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge_aws.facts.streaming_pipeline import build_streaming_pipeline
from sparkforge_aws.findings.models import Fact, sort_facts
from sparkforge_aws.findings.validate import validate_fact, validate_finding
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_pipeline"
REQUIRED_FIXTURES = {"complete", "selector_missing", "selector_ambiguous", "contract_invalid"}


def _facts(path: Path) -> list[Fact]:
    payloads = json.loads((path / "input/facts.json").read_text(encoding="utf-8"))
    return [Fact(**payload) for payload in payloads]


def _run(path: Path):
    meta = yaml.safe_load((path / "meta.yaml").read_text(encoding="utf-8"))
    contract = json.loads((path / "input/contract.json").read_text(encoding="utf-8"))
    facts = sort_facts(build_streaming_pipeline(_facts(path), contract))
    findings = judge(facts, load_catalog(), {})
    return meta, facts, findings


def test_streaming_pipeline_fixture_corpus_is_complete():
    assert {path.name for path in FIXTURES.iterdir() if path.is_dir()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", sorted(REQUIRED_FIXTURES))
def test_streaming_pipeline_fixture_goldens(directory: str):
    path = FIXTURES / directory
    meta, facts, findings = _run(path)
    expected_facts = json.loads((path / "expected/facts.json").read_text(encoding="utf-8"))
    expected_findings = json.loads((path / "expected/findings.json").read_text(encoding="utf-8"))

    assert [fact.to_dict() for fact in facts] == expected_facts
    assert [finding.to_dict() for finding in findings] == expected_findings
    assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
    assert {finding.rule_id for finding in findings} == set(meta["expects_findings"])
    assert len({fact.id for fact in facts}) == len(facts)
    for fact in facts:
        validate_fact(fact.to_dict())
    for finding in findings:
        validate_finding(finding.to_dict())
