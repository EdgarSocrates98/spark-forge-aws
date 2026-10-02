from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.facts.iceberg_metadata import extract_iceberg_metadata_path
from sparkforge.facts.streaming import extract_streaming_progress_path
from sparkforge.facts.streaming_ops import extract_streaming_ops_path
from sparkforge.facts.streaming_composition import build_streaming_composition
from sparkforge.facts.transport import extract_transport_path
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_composition"
REQUIRED_FIXTURES = {
    "iceberg_non_append",
    "iceberg_temporal_append",
    "iceberg_temporal_non_append",
    "iceberg_temporal_unresolved",
    "observability_lag",
    "observability_kinesis",
    "unresolved_link",
    "slo_met",
    "slo_violated",
    "slo_unresolved",
    "slo_kafka_met",
    "slo_kinesis_violated",
    "slo_transport_unresolved",
    "slo_sink_met",
    "slo_sink_violated",
    "slo_sink_unresolved",
}


def _facts(directory: Path):
    facts = []
    for path in sorted((directory / "input").iterdir()):
        if path.name == "progress.jsonl":
            facts.extend(extract_streaming_progress_path(path))
        elif path.name == "contract.json":
            facts.extend(extract_streaming_ops_path(path))
        elif path.name == "iceberg.json":
            facts.extend(extract_iceberg_metadata_path(path))
        elif path.name == "kafka.json":
            facts.extend(extract_transport_path(path, artifact_type="kafka"))
        elif path.name == "kinesis.json":
            facts.extend(extract_transport_path(path, artifact_type="kinesis"))
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
                table=meta.get("table", ""),
                query_name=meta.get("query_name", ""),
                slo_name=meta.get("slo_name", ""),
                transport_key=meta.get("transport_key", ""),
                max_skew_seconds=meta.get("max_skew_seconds"),
            )
        )
        findings = judge(facts, load_catalog(), {})
        assert [fact.to_dict() for fact in facts] == json.loads(
            (directory / "expected/facts.json").read_text(encoding="utf-8")
        )
        assert [finding.to_dict() for finding in findings] == json.loads(
            (directory / "expected/findings.json").read_text(encoding="utf-8")
        )
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        assert {finding.rule_id for finding in findings} >= set(meta["expects_findings"])
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())
