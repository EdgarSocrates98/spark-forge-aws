from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_streaming_glue_runtime_observation import _run_fixture

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_glue_runtime_observation"


@pytest.mark.parametrize(
    "directory", sorted(FIXTURES.glob("*/")), ids=lambda path: path.name
)
def test_streaming_glue_runtime_observation_golden(directory: Path):
    meta, facts, findings = _run_fixture(directory)
    expected_facts = json.loads(
        (directory / "expected" / "facts.json").read_text(encoding="utf-8")
    )
    expected_findings = json.loads(
        (directory / "expected" / "findings.json").read_text(encoding="utf-8")
    )
    assert [fact.to_dict() for fact in facts] == expected_facts
    assert [finding.to_dict() for finding in findings] == expected_findings
    assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
