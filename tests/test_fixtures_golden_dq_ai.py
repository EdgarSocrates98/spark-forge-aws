import json
from pathlib import Path

import yaml

from sparkforge.adapters import _core
from sparkforge.facts.athena_cost import extract_athena_cost_path
from sparkforge.facts.glue_dq_advanced import (
    extract_dq_review_path,
    extract_glue_dq_advanced_tree,
)
from sparkforge.dqdl.validator import validate_dqdl_path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "dq_ai"


def _case_facts(directory: Path):
    facts = extract_glue_dq_advanced_tree(directory / "input")
    dqdl = directory / "input" / "rules.dqdl"
    if dqdl.exists():
        facts.extend(validate_dqdl_path(dqdl))
    review = directory / "input" / "review.json"
    if review.exists():
        facts.extend(extract_dq_review_path(review))
    cost = directory / "input" / "cost.json"
    if cost.exists():
        facts.extend(extract_athena_cost_path(cost))
    return facts


def _runtime(meta):
    return str((meta.get("runtime") or {}).get("glue") or "")


def test_every_dq_ai_fixture_matches_declared_kinds_and_rules(tmp_path):
    for directory in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = _case_facts(directory)
        facts_path = tmp_path / f"{directory.name}.json"
        facts_path.write_text(
            json.dumps([fact.to_dict() for fact in facts]), encoding="utf-8"
        )
        dqdl = directory / "input" / "rules.dqdl"
        review = directory / "input" / "review.json"
        cost = directory / "input" / "cost.json"
        report = _core.dq_ai_assess(
            [str(facts_path)],
            dqdl_path=str(dqdl) if dqdl.exists() else "",
            review_path=str(review) if review.exists() else "",
            cost_facts_path=str(cost) if cost.exists() else "",
            glue=_runtime(meta) or None,
        )
        expected_facts = json.loads(
            (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        )
        expected_findings = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        observed_kinds = {
            fact["kind"]
            for fact in report["facts"]
            if fact["kind"].startswith("dq.") or fact["kind"].startswith("athena.")
        }
        assert observed_kinds == {
            fact["kind"] for fact in expected_facts
        }
        assert [finding["rule_id"] for finding in report["findings"]] == [
            finding["rule_id"] for finding in expected_findings
        ]
        assert set(report["views"]) == {"maintainer", "operator", "security_compliance"}
