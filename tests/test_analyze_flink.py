from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge.adapters._core import analyze_flink
from sparkforge.adapters.tools import TOOLS, call_tool

ROOT = Path(__file__).resolve().parents[1]
FLINK = ROOT / "fixtures" / "flink" / "flink_positive" / "input" / "dump.json"


def test_cli_and_mcp_flink_envelopes_match():
    expected = analyze_flink(str(FLINK), artifact="flink", limit=4)
    actual = call_tool(
        "sparkforge_analyze_flink",
        {"path": str(FLINK), "artifact": "flink", "limit": 4},
    )
    assert actual == expected
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge.adapters.cli",
            "analyze",
            "flink",
            "--path",
            str(FLINK),
            "--artifact",
            "flink",
            "--limit",
            "4",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_flink_tool_is_read_only_and_schema_declared():
    spec = TOOLS["sparkforge_analyze_flink"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["path", "artifact"]
    assert spec["inputSchema"]["properties"]["artifact"]["enum"] == ["flink", "managed_flink"]
