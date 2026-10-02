from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge.adapters._core import analyze_streaming_composition
from sparkforge.adapters.tools import TOOLS, call_tool

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/streaming_composition/observability_lag/input"
PROGRESS = ROOT / "fixtures/streaming_composition/observability_lag/expected/progress.json"
KAFKA = ROOT / "fixtures/streaming_composition/observability_lag/expected/kafka.json"


def _paths(tmp_path: Path) -> list[str]:
    progress = tmp_path / "progress.json"
    kafka = tmp_path / "kafka.json"
    progress_facts = json.loads(
        (ROOT / "fixtures/streaming_composition/observability_lag/expected/facts.json").read_text(
            encoding="utf-8"
        )
    )
    progress.write_text(
        json.dumps([fact for fact in progress_facts if fact["kind"].startswith("streaming.progress")]),
        encoding="utf-8",
    )
    kafka.write_text(
        json.dumps([fact for fact in progress_facts if fact["kind"].startswith("kafka.")]),
        encoding="utf-8",
    )
    return [str(progress), str(kafka)]


def test_cli_and_mcp_envelopes_match(tmp_path: Path):
    paths = _paths(tmp_path)
    args = {
        "facts_paths": paths,
        "mode": "observability",
        "query_name": "orders-query",
        "transport_key": "orders-group",
        "limit": 20,
    }
    expected = analyze_streaming_composition(**args)
    actual = call_tool("sparkforge_analyze_streaming_composition", args)
    assert actual == expected
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge.adapters.cli",
            "analyze",
            "streaming-composition",
            "--facts",
            paths[0],
            "--facts",
            paths[1],
            "--mode",
            "observability",
            "--query-name",
            "orders-query",
            "--transport-key",
            "orders-group",
            "--limit",
            "20",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_tool_is_read_only_and_declared():
    spec = TOOLS["sparkforge_analyze_streaming_composition"]
    assert spec["annotations"]["readOnlyHint"] is True
    assert spec["inputSchema"]["required"] == ["facts_paths", "mode"]
