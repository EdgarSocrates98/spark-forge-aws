from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge_aws.facts.streaming_ops import extract_streaming_ops_path
from sparkforge_aws.findings.models import sort_facts
from sparkforge_aws.findings.validate import validate_fact, validate_finding
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_ops"


def test_streaming_ops_goldens():
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = sort_facts(
            extract_streaming_ops_path(directory / meta["artifact"], repo_root=directory / "input")
        )
        findings = judge(facts, load_catalog(), {})
        assert [fact.to_dict() for fact in facts] == json.loads(
            (directory / "expected/facts.json").read_text(encoding="utf-8")
        )
        assert [finding.to_dict() for finding in findings] == json.loads(
            (directory / "expected/findings.json").read_text(encoding="utf-8")
        )
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        assert {finding.rule_id for finding in findings} == set(meta["expects_findings"])
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())
