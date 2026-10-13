from pathlib import Path

from sparkforge_aws.facts.glue_streaming import extract_glue_streaming_path
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).parents[1]
RULES = [r for r in load_catalog() if r["id"].startswith("SF-GLUESTREAM-")]


def test_rtm_capacity_gap_is_named_without_inventing_partition_count():
    facts = extract_glue_streaming_path(
        ROOT / "fixtures/glue_streaming/rtm_missing_capacity/input/job.json"
    )
    findings = judge(facts, RULES, runtime={})
    assert {finding.rule_id for finding in findings} == {"SF-GLUESTREAM-002"}
    assert findings[0].evidence


def test_valid_rtm_does_not_fire_constraint_rules():
    facts = extract_glue_streaming_path(ROOT / "fixtures/glue_streaming/rtm_valid/input/job.json")
    findings = judge(facts, RULES, runtime={})
    assert findings == []
