from __future__ import annotations

from pathlib import Path

from sparkforge.facts.schema_registry import extract_schema_registry_path

ROOT = Path(__file__).resolve().parents[1]


def test_schema_registry_extracts_diff_and_unresolved_policy():
    compatible = extract_schema_registry_path(
        ROOT / "fixtures/schema_registry/schema_compatible/input/contract.json"
    )
    assert "schema.diff" in {fact.kind for fact in compatible}
    diff = next(fact for fact in compatible if fact.kind == "schema.diff")
    assert diff.attrs["compatible"] is True
    unresolved = extract_schema_registry_path(
        ROOT / "fixtures/schema_registry/schema_unresolved/input/contract.json"
    )
    assert any(fact.attrs.get("reason") == "compatibility_not_declared" for fact in unresolved)


def test_schema_registry_invalid_json_is_named():
    facts = extract_schema_registry_path(
        ROOT / "fixtures/schema_registry/schema_invalid/input/broken.json"
    )
    assert [fact.kind for fact in facts] == ["schema.unresolved"]
    assert facts[0].attrs["reason"] == "invalid_json"
