from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge.adapters._core import analyze_glue_streaming
from sparkforge.adapters.tools import TOOLS, call_tool

ROOT = Path(__file__).resolve().parents[1]
GLUE = ROOT / "fixtures" / "glue_streaming" / "rtm_valid" / "input" / "job.json"


def test_cli_and_mcp_glue_streaming_envelopes_match():
    expected = analyze_glue_streaming(str(GLUE), limit=3)
    actual = call_tool("sparkforge_analyze_glue_streaming", {"path": str(GLUE), "limit": 3})
    assert actual == expected
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge.adapters.cli",
            "analyze",
            "glue-streaming",
            "--path",
            str(GLUE),
            "--limit",
            "3",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_glue_streaming_tool_is_read_only_and_schema_declared():
    spec = TOOLS["sparkforge_analyze_glue_streaming"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["path"]
