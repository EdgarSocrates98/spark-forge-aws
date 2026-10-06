from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge.adapters._core import analyze_streaming
from sparkforge.adapters.tools import TOOLS, call_tool

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "fixtures" / "streaming" / "progress_positive" / "input" / "progress.jsonl"
SOURCE = ROOT / "fixtures" / "streaming" / "source_positive" / "input" / "job.py"


def test_streaming_core_and_mcp_share_progress_contract():
    expected = analyze_streaming(str(PROGRESS), artifact="progress", limit=3)
    actual = call_tool(
        "sparkforge_analyze_streaming",
        {"path": str(PROGRESS), "artifact": "progress", "limit": 3},
    )
    # `_trust` e aditivo em todo resultado de call_tool (FASE 3); o contrato
    # do envelope e comparado sem ele, e o formato e travado em
    # tests/test_runtime_convergence_trust.py.
    actual.pop("_trust", None)
    assert actual == expected
    assert expected["unresolved"] == 0
    assert expected["by_kind"]["streaming.progress.series"] == 1


def test_streaming_source_uses_same_page_shape():
    result = analyze_streaming(
        str(SOURCE), artifact="source", kind=["streaming.query"], limit=10
    )
    assert set(
        [
            "total_count",
            "returned_count",
            "next_cursor",
            "filters_applied",
            "by_kind",
            "unresolved",
            "unresolved_at",
            "items",
        ]
    ) <= result.keys()
    assert result["total_count"] >= 2
    assert all(item["kind"] == "streaming.query" for item in result["items"])


def test_cli_and_core_emit_identical_streaming_envelope():
    expected = analyze_streaming(str(PROGRESS), artifact="progress", limit=2)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge.adapters.cli",
            "analyze",
            "streaming",
            "--path",
            str(PROGRESS),
            "--artifact",
            "progress",
            "--limit",
            "2",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_streaming_tool_is_read_only_and_schema_declared():
    spec = TOOLS["sparkforge_analyze_streaming"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["path", "artifact"]
