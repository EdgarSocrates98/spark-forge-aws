from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge_aws.adapters._core import analyze_transport
from sparkforge_aws.adapters.tools import TOOLS, call_tool

ROOT = Path(__file__).resolve().parents[1]
KAFKA = ROOT / "fixtures" / "transport" / "kafka_positive" / "input" / "dump.json"


def test_cli_and_mcp_transport_envelopes_match():
    expected = analyze_transport(str(KAFKA), artifact="kafka", limit=4)
    actual = call_tool(
        "sparkforge_aws_analyze_transport",
        {"path": str(KAFKA), "artifact": "kafka", "limit": 4},
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
            "transport",
            "--path",
            str(KAFKA),
            "--artifact",
            "kafka",
            "--limit",
            "4",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_transport_tool_is_read_only_and_schema_declared():
    spec = TOOLS["sparkforge_aws_analyze_transport"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["path", "artifact"]
    assert spec["inputSchema"]["properties"]["artifact"]["enum"] == [
        "kafka",
        "msk",
        "kinesis",
    ]
