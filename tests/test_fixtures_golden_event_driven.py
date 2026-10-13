from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge_aws.facts.event_driven import extract_event_driven_path
from sparkforge_aws.findings.models import sort_facts
from sparkforge_aws.findings.validate import validate_fact, validate_finding
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "event_driven"


def test_event_driven_goldens():
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = sort_facts(
            extract_event_driven_path(directory / meta["artifact"], repo_root=directory / "input")
        )
        findings = judge(facts, load_catalog(), {})
        assert [f.to_dict() for f in facts] == json.loads(
            (directory / "expected/facts.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == json.loads(
            (directory / "expected/findings.json").read_text(encoding="utf-8")
        )
        assert {f.kind for f in facts} == set(meta["expects_kinds"])
        assert {f.rule_id for f in findings} == set(meta["expects_findings"])
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())
