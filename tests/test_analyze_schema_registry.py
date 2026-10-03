from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge.adapters._core import analyze_schema_registry
from sparkforge.adapters.tools import TOOLS, call_tool


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "fixtures" / "schema_registry" / "schema_compatible" / "input" / "contract.json"


def test_cli_and_mcp_schema_registry_envelopes_match():
    expected = analyze_schema_registry(str(CONTRACT), limit=4)
    actual = call_tool("sparkforge_analyze_schema_registry", {"path": str(CONTRACT), "limit": 4})
    assert actual == expected
    completed = subprocess.run(
        [sys.executable, "-m", "sparkforge.adapters.cli", "analyze", "schema-registry", "--path", str(CONTRACT), "--limit", "4"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_schema_registry_tool_is_read_only_and_declared():
    spec = TOOLS["sparkforge_analyze_schema_registry"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["path"]
