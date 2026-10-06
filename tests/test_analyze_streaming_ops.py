from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge_aws.adapters._core import analyze_streaming_ops
from sparkforge_aws.adapters.tools import TOOLS, call_tool

ROOT = Path(__file__).resolve().parents[1]


def test_cli_and_mcp_envelopes_match(tmp_path: Path):
    dump = tmp_path / "streaming-ops.json"
    dump.write_text(
        json.dumps({"slo": [{"name": "latency", "metric": "p95", "target": 5, "unit": "s"}]}),
        encoding="utf-8",
    )
    expected = analyze_streaming_ops(str(dump), limit=20)
    actual = call_tool("sparkforge_analyze_streaming_ops", {"path": str(dump), "limit": 20})
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
            "streaming-ops",
            "--path",
            str(dump),
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
    spec = TOOLS["sparkforge_analyze_streaming_ops"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["path"]
