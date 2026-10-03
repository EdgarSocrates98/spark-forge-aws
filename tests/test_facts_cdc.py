from __future__ import annotations

from pathlib import Path

from sparkforge.facts.cdc import extract_cdc_path

ROOT = Path(__file__).resolve().parents[1]


def kinds(facts):
    return {fact.kind for fact in facts}


def test_cdc_events_preserve_position_transaction_delete_and_duplicate():
    facts = extract_cdc_path(
        ROOT / "fixtures" / "cdc" / "cdc_events" / "input" / "events.jsonl", artifact="cdc"
    )
    assert {
        "cdc.event",
        "cdc.snapshot",
        "cdc.transaction",
        "cdc.duplicate",
        "cdc.analyzed",
    } <= kinds(facts)
    delete = next(f for f in facts if f.kind == "cdc.event" and f.attrs["operation"] == "DELETE")
    assert delete.attrs["source_position"] == "12"
    assert delete.attrs["tombstone"] is False
    assert next(f for f in facts if f.kind == "cdc.duplicate").attrs["source_position"] == "12"


def test_debezium_and_dms_keep_configuration_and_unresolved_separate():
    debezium = extract_cdc_path(
        ROOT / "fixtures" / "cdc" / "debezium_valid" / "input" / "connector.json",
        artifact="debezium",
    )
    dms = extract_cdc_path(
        ROOT / "fixtures" / "cdc" / "dms_missing" / "input" / "task.json", artifact="dms"
    )
    assert {"debezium.connector", "debezium.status", "debezium.analyzed"} <= kinds(debezium)
    assert {"dms.task", "dms.unresolved", "dms.analyzed"} <= kinds(dms)
    assert any(
        f.attrs["reason"] == "missing_table_mappings" for f in dms if f.kind == "dms.unresolved"
    )


def test_cdc_invalid_json_is_unresolved():
    facts = extract_cdc_path(
        ROOT / "fixtures" / "cdc" / "cdc_invalid" / "input" / "bad.json", artifact="cdc"
    )
    assert any(f.kind == "cdc.unresolved" and f.attrs["reason"] == "invalid_json" for f in facts)
