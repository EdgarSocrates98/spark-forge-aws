from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge.adapters._core import analyze_streaming_composition
from sparkforge.adapters.tools import call_tool
from sparkforge.facts.streaming_pipeline import build_streaming_pipeline
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]


def _fact(kind: str, symbol: str, attrs: dict) -> Fact:
    return Fact(
        kind=kind,
        subject={
            "type": "source_location",
            "file": f"{symbol}.json",
            "line": 1,
            "col": 0,
            "symbol": symbol,
            "snippet": "",
        },
        attrs=attrs,
        provenance={
            "artifact": f"{symbol}.json",
            "artifact_sha256": f"sha-{symbol}",
            "extractor": "test@0.1.0",
        },
    )


def _contract() -> dict:
    return {
        "schema_version": 1,
        "pipeline_id": "orders",
        "nodes": [
            {"id": "cdc", "selector": {"kind": "cdc.event", "attrs": {"topic": "orders"}}},
            {
                "id": "transport",
                "selector": {
                    "kind": "kafka.partition",
                    "attrs": {"topic": "orders", "partition": 0},
                },
            },
            {
                "id": "processor",
                "selector": {"kind": "flink.job", "attrs": {"job_name": "orders-job"}},
            },
            {
                "id": "sink",
                "selector": {
                    "kind": "iceberg.snapshots_summary",
                    "attrs": {"table": "catalog.db.orders"},
                },
            },
        ],
        "edges": [
            {"id": "cdc-to-kafka", "from": "cdc", "to": "transport"},
            {"id": "kafka-to-flink", "from": "transport", "to": "processor"},
            {"id": "flink-to-iceberg", "from": "processor", "to": "sink"},
        ],
    }


def _facts() -> list[Fact]:
    return [
        _fact("cdc.event", "cdc-1", {"topic": "orders", "operation": "u"}),
        _fact("kafka.partition", "partition-0", {"topic": "orders", "partition": 0}),
        _fact("flink.job", "flink-1", {"job_name": "orders-job"}),
        _fact("iceberg.snapshots_summary", "table-1", {"table": "catalog.db.orders"}),
    ]


def test_pipeline_contract_emits_verified_nodes_and_edges():
    facts = _facts()
    composed = build_streaming_pipeline(facts, _contract())

    nodes = [fact for fact in composed if fact.kind == "streaming.pipeline.node"]
    links = [fact for fact in composed if fact.kind == "streaming.pipeline.link"]
    summary = next(fact for fact in composed if fact.kind == "streaming.pipeline")

    assert len(nodes) == 4
    assert len(links) == 3
    assert all(fact.attrs["status"] == "verified" for fact in nodes + links)
    assert summary.attrs["status"] == "verified"
    assert summary.measures["verified_edge_count"] == 3
    assert all(fact.attrs["source_fact_ids"] for fact in nodes + links)
    assert not [fact for fact in composed if fact.kind == "streaming.pipeline.unresolved"]

    ambiguous = _facts() + [
        _fact("kafka.partition", "partition-1", {"topic": "orders", "partition": 0})
    ]
    unresolved = build_streaming_pipeline(ambiguous, _contract())
    reasons = {
        fact.attrs["reason"] for fact in unresolved if fact.kind == "streaming.pipeline.unresolved"
    }
    assert "selector_ambiguous" in reasons
    assert not [
        fact
        for fact in unresolved
        if fact.kind == "streaming.pipeline.link"
        and fact.attrs["status"] == "verified"
        and fact.attrs["edge_id"] == "cdc-to-kafka"
    ]


def test_pipeline_rule_fires_only_for_observed_blind_spot():
    complete = build_streaming_pipeline(_facts(), _contract())
    assert not {
        finding.rule_id
        for finding in judge(complete, load_catalog(), {})
        if finding.rule_id == "SF-STREAM-015"
    }

    missing = _contract()
    missing["nodes"][-1]["selector"]["attrs"]["table"] = "catalog.db.missing"
    incomplete = build_streaming_pipeline(_facts(), missing)
    findings = judge(incomplete, load_catalog(), {})
    assert "SF-STREAM-015" in {finding.rule_id for finding in findings}
    assert all(finding.evidence for finding in findings)


def test_pipeline_cli_mcp_envelopes_match(tmp_path: Path):
    facts_path = tmp_path / "facts.json"
    contract_path = tmp_path / "pipeline.json"
    facts_path.write_text(json.dumps([fact.to_dict() for fact in _facts()]), encoding="utf-8")
    contract_path.write_text(json.dumps(_contract()), encoding="utf-8")
    args = {
        "facts_paths": [str(facts_path)],
        "pipeline_path": str(contract_path),
        "mode": "pipeline",
        "limit": 100,
    }

    expected = analyze_streaming_composition(**args)
    actual = call_tool("sparkforge_analyze_streaming_composition", args)
    # `_trust` e aditivo em todo resultado de call_tool (FASE 3); o contrato
    # do envelope e comparado sem ele, e o formato e travado em
    # tests/test_runtime_convergence_trust.py.
    actual.pop("_trust", None)
    assert actual == expected
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge.adapters.cli",
            "analyze",
            "streaming-composition",
            "--facts",
            str(facts_path),
            "--pipeline-path",
            str(contract_path),
            "--mode",
            "pipeline",
            "--limit",
            "100",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert json.loads(completed.stdout) == expected
