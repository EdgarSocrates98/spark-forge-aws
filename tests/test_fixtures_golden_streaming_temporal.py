from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.facts.streaming import extract_streaming_progress_path
from sparkforge.facts.streaming_composition import build_streaming_composition
from sparkforge.facts.transport import extract_transport_path
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_temporal"
REQUIRED_FIXTURES = {"kafka_paired", "kinesis_paired", "missing_timestamp"}


def _facts(directory: Path):
    facts = list(extract_streaming_progress_path(directory / "input" / "progress.jsonl"))
    if (directory / "input" / "kafka.json").exists():
        facts.extend(
            extract_transport_path(directory / "input" / "kafka.json", artifact_type="kafka")
        )
    if (directory / "input" / "kinesis.json").exists():
        facts.extend(
            extract_transport_path(directory / "input" / "kinesis.json", artifact_type="kinesis")
        )
    runtime_file = directory / "runtime.json"
    if runtime_file.exists():
        _, runtime_facts = detect_runtime(json.loads(runtime_file.read_text(encoding="utf-8")))
        facts.extend(runtime_facts)
    return facts


def test_fixture_corpus_is_complete():
    assert {path.name for path in FIXTURES.iterdir() if path.is_dir()} == REQUIRED_FIXTURES


def test_fixture_goldens():
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = sort_facts(
            build_streaming_composition(
                _facts(directory),
                mode=meta["mode"],
                query_name=meta["query_name"],
                transport_key=meta["transport_key"],
                max_skew_seconds=meta["max_skew_seconds"],
            )
        )
        temporal = [fact for fact in facts if fact.kind == "streaming.temporal.diagnostic"]
        assert len(temporal) == (1 if meta["expects_pairs"] else 0)
        if temporal:
            assert temporal[0].measures["paired_observation_count"] == meta["expects_pairs"]
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        findings = judge(facts, load_catalog(), {})
        assert {finding.rule_id for finding in findings} >= set(meta["expects_findings"])
        for fact in facts:
            validate_fact(fact.to_dict())
