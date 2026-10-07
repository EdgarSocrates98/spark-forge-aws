from pathlib import Path

from sparkforge_aws.facts.cdc import extract_cdc_tree
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
RULES = load_catalog()


def _finding_ids(name: str):
    facts = extract_cdc_tree(ROOT / "fixtures" / "cdc" / name / "input", artifact={
        "cdc_events": "cdc",
        "cdc_missing_key": "cdc",
        "debezium_unresolved": "debezium",
        "dms_missing": "dms",
    }[name])
    return {finding.rule_id for finding in judge(facts, RULES, {})}


def test_cdc_duplicate_and_delete_rules_fire_only_on_observed_values():
    assert {"SF-CDC-002", "SF-CDC-003"} <= _finding_ids("cdc_events")
    assert "SF-CDC-003" not in _finding_ids("cdc_missing_key")


def test_debezium_unresolved_and_dms_seam_rules_are_separate():
    assert {"SF-DEBEZIUM-001", "SF-DEBEZIUM-002"} <= _finding_ids("debezium_unresolved")
    assert {"SF-DMS-001", "SF-DMS-002", "SF-DMS-003"} <= _finding_ids("dms_missing")
