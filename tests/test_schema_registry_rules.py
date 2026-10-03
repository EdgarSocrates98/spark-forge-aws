from __future__ import annotations

from pathlib import Path

from sparkforge.facts.schema_registry import extract_schema_registry_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog


ROOT = Path(__file__).resolve().parents[1]


def _findings(name: str):
    facts = extract_schema_registry_tree(ROOT / "fixtures/schema_registry" / name / "input")
    return judge(facts, load_catalog(), {})


def test_incompatible_schema_and_auto_registration_are_findings():
    ids = {finding.rule_id for finding in _findings("schema_incompatible")}
    assert {"SF-SCHEMA-001", "SF-SCHEMA-002"} <= ids


def test_missing_compatibility_is_p0_finding():
    ids = {finding.rule_id for finding in _findings("schema_unresolved")}
    assert "SF-SCHEMA-003" in ids
