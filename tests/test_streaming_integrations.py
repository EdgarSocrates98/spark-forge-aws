from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from sparkforge_aws.adapters._core import analyze_streaming_integrations
from sparkforge_aws.adapters.tools import TOOLS, call_tool
from sparkforge_aws.facts.streaming_integrations import extract_streaming_integrations_path
from sparkforge_aws.findings.validate import validate_fact, validate_finding
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_integrations"


def test_goldens_cover_checkpoint_connect_streams_and_openlineage():
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = extract_streaming_integrations_path(
            directory / meta["artifact"], repo_root=directory / "input"
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
        assert len({fact.id for fact in facts}) == len(facts)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())


def test_cli_and_mcp_envelopes_match(tmp_path: Path):
    source = tmp_path / "integrations.json"
    source.write_text(
        json.dumps(
            {
                "openlineage": {
                    "eventType": "COMPLETE",
                    "job": {"name": "job"},
                    "run": {"runId": "run"},
                    "inputs": [],
                    "outputs": [],
                }
            }
        ),
        encoding="utf-8",
    )
    expected = analyze_streaming_integrations(str(source), limit=20)
    actual = call_tool(
        "sparkforge_analyze_streaming_integrations", {"path": str(source), "limit": 20}
    )
    # `_trust` e aditivo em todo resultado de call_tool (FASE 3); o contrato
    # do envelope e comparado sem ele, e o formato e travado em
    # tests/test_runtime_convergence_trust.py.
    actual.pop("_trust", None)
    assert actual == expected
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge_aws.adapters.cli",
            "analyze",
            "streaming-integrations",
            "--path",
            str(source),
            "--limit",
            "20",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert json.loads(completed.stdout) == expected


def test_tool_is_read_only_and_declared():
    spec = TOOLS["sparkforge_analyze_streaming_integrations"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["path"]
