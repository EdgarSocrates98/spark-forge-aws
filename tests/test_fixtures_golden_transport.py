from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge_aws.facts.transport import extract_transport_tree
from sparkforge_aws.findings.models import sort_facts
from sparkforge_aws.findings.validate import validate_fact

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "transport"
REQUIRED_FIXTURES = {
    "kafka_isr_deficit",
    "kafka_lag_series",
    "kafka_positive",
    "kafka_unresolved",
    "msk_positive",
    "msk_unresolved",
    "kinesis_positive",
    "unresolved",
}


def fixture_dirs():
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    return meta, sort_facts(
        extract_transport_tree(
            directory / "input", artifact_type=meta["artifact"], repo_root=directory / "input"
        )
    )


def test_transport_fixture_corpus_is_complete():
    assert {path.name for path in fixture_dirs()} == REQUIRED_FIXTURES
    for directory in fixture_dirs():
        meta, facts = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [fact.to_dict() for fact in facts] == expected
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        for fact in facts:
            validate_fact(fact.to_dict())


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda path: path.name)
def test_transport_extraction_is_deterministic(directory):
    first = run_fixture(directory)[1]
    second = run_fixture(directory)[1]
    assert [fact.to_dict() for fact in first] == [fact.to_dict() for fact in second]
