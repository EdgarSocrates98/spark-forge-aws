from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_streaming_glue_cross_artifact import _run_fixture

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_glue_cross_artifact"


@pytest.mark.parametrize(
    "directory", sorted(FIXTURES.glob("*/")), ids=lambda path: path.name
)
def test_streaming_glue_cross_artifact_golden(directory: Path):
    _, facts, findings = _run_fixture(directory)
    expected_facts = json.loads(
        (directory / "expected" / "facts.json").read_text(encoding="utf-8")
    )
    expected_findings = json.loads(
        (directory / "expected" / "findings.json").read_text(encoding="utf-8")
    )
    assert [fact.to_dict() for fact in facts] == expected_facts
    assert [finding.to_dict() for finding in findings] == expected_findings
