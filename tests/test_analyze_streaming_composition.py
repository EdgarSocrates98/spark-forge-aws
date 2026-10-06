from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sparkforge_aws.adapters._core import analyze_streaming_composition
from sparkforge_aws.adapters.tools import TOOLS, call_tool

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
        json.dumps(
            [fact for fact in progress_facts if fact["kind"].startswith("streaming.progress")]
        ),
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


def test_temporal_cli_and_mcp_envelopes_match(tmp_path: Path):
    progress = tmp_path / "progress-temporal.json"
    kafka = tmp_path / "kafka-temporal.json"
    progress.write_text(
        json.dumps(
            [
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 1, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:00:00Z"},
                    "measures": {
                        "batch_id": 1,
                        "input_rows_per_second": 100,
                        "processed_rows_per_second": 80,
                    },
                },
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 2, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:00:10Z"},
                    "measures": {
                        "batch_id": 2,
                        "input_rows_per_second": 110,
                        "processed_rows_per_second": 90,
                    },
                },
            ]
        ),
        encoding="utf-8",
    )
    kafka.write_text(
        json.dumps(
            [
                {
                    "kind": "kafka.lag",
                    "subject": {"type": "source_location", "file": "kafka", "line": 1, "col": 0},
                    "attrs": {"group": "orders-group", "topic": "orders"},
                    "measures": {"partition": 0, "lag": 30, "timestamp": 1790942401},
                },
                {
                    "kind": "kafka.lag",
                    "subject": {"type": "source_location", "file": "kafka", "line": 2, "col": 0},
                    "attrs": {"group": "orders-group", "topic": "orders"},
                    "measures": {"partition": 0, "lag": 40, "timestamp": 1790942412},
                },
            ]
        ),
        encoding="utf-8",
    )
    args = {
        "facts_paths": [str(progress), str(kafka)],
        "mode": "temporal",
        "query_name": "orders-query",
        "transport_key": "orders-group",
        "max_skew_seconds": 3,
        "limit": 20,
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
            "sparkforge_aws.adapters.cli",
            "analyze",
            "streaming-composition",
            "--facts",
            str(progress),
            "--facts",
            str(kafka),
            "--mode",
            "temporal",
            "--query-name",
            "orders-query",
            "--transport-key",
            "orders-group",
            "--max-skew-seconds",
            "3",
            "--limit",
            "20",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_iceberg_temporal_cli_and_mcp_envelopes_match(tmp_path: Path):
    progress = tmp_path / "progress-iceberg-temporal.json"
    iceberg = tmp_path / "iceberg-iceberg-temporal.json"
    progress.write_text(
        json.dumps(
            [
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 1, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:00:00Z"},
                    "measures": {"batch_id": 1},
                },
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 2, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:00:10Z"},
                    "measures": {"batch_id": 2},
                },
            ]
        ),
        encoding="utf-8",
    )
    iceberg.write_text(
        json.dumps(
            [
                {
                    "kind": "iceberg.snapshot",
                    "subject": {
                        "type": "snapshot",
                        "file": "metadata",
                        "symbol": "db.events",
                        "snapshot_id": 101,
                    },
                    "attrs": {
                        "snapshot_id": 101,
                        "committed_at": "2026-10-02T12:00:00Z",
                        "timestamp_observed": True,
                        "operation_observed": True,
                        "operation": "append",
                    },
                    "measures": {"snapshot_index": 0},
                },
                {
                    "kind": "iceberg.snapshot",
                    "subject": {
                        "type": "snapshot",
                        "file": "metadata",
                        "symbol": "db.events",
                        "snapshot_id": 102,
                    },
                    "attrs": {
                        "snapshot_id": 102,
                        "committed_at": "2026-10-02T12:00:10Z",
                        "timestamp_observed": True,
                        "operation_observed": True,
                        "operation": "replace",
                    },
                    "measures": {"snapshot_index": 1},
                },
            ]
        ),
        encoding="utf-8",
    )
    args = {
        "facts_paths": [str(progress), str(iceberg)],
        "mode": "iceberg_temporal",
        "table": "db.events",
        "query_name": "orders-query",
        "max_skew_seconds": 0,
        "limit": 20,
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
            "sparkforge_aws.adapters.cli",
            "analyze",
            "streaming-composition",
            "--facts",
            str(progress),
            "--facts",
            str(iceberg),
            "--mode",
            "iceberg_temporal",
            "--table",
            "db.events",
            "--query-name",
            "orders-query",
            "--max-skew-seconds",
            "0",
            "--limit",
            "20",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_slo_cli_and_mcp_envelopes_match(tmp_path: Path):
    contract = tmp_path / "contract.json"
    progress = tmp_path / "progress.json"
    contract.write_text(
        json.dumps(
            [
                {
                    "kind": "streaming.slo",
                    "subject": {
                        "type": "source_location",
                        "file": "contract",
                        "line": 1,
                        "col": 0,
                        "symbol": "throughput",
                    },
                    "attrs": {
                        "name": "throughput",
                        "metric": "processed_rows_per_second",
                        "operator": "gte",
                        "unit": "rows_per_second",
                        "window": "5m",
                        "source": "spark_progress",
                    },
                    "measures": {"target": 95},
                }
            ]
        ),
        encoding="utf-8",
    )
    progress.write_text(
        json.dumps(
            [
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 1, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:00:00Z"},
                    "measures": {"batch_id": 1, "processed_rows_per_second": 100},
                },
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 2, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:05:00Z"},
                    "measures": {"batch_id": 2, "processed_rows_per_second": 90},
                },
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 3, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:10:00Z"},
                    "measures": {"batch_id": 3, "processed_rows_per_second": 110},
                },
            ]
        ),
        encoding="utf-8",
    )
    args = {
        "facts_paths": [str(contract), str(progress)],
        "mode": "slo",
        "slo_name": "throughput",
        "query_name": "orders-query",
        "limit": 20,
    }
    expected = analyze_streaming_composition(**args)
    actual = call_tool("sparkforge_analyze_streaming_composition", args)
    # `_trust` e aditivo em todo resultado de call_tool (FASE 3); o contrato
    # do envelope e comparado sem ele, e o formato e travado em
    # tests/test_runtime_convergence_trust.py.
    actual.pop("_trust", None)
    assert actual == expected
    assert any(
        item["kind"] == "streaming.slo.evaluation" and item["attrs"]["status"] == "violated"
        for item in expected["items"]
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge_aws.adapters.cli",
            "analyze",
            "streaming-composition",
            "--facts",
            str(contract),
            "--facts",
            str(progress),
            "--mode",
            "slo",
            "--slo-name",
            "throughput",
            "--query-name",
            "orders-query",
            "--limit",
            "20",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected


def test_transport_slo_cli_and_mcp_envelopes_match(tmp_path: Path):
    contract = tmp_path / "contract-transport.json"
    kafka = tmp_path / "kafka-transport.json"
    contract.write_text(
        json.dumps(
            [
                {
                    "kind": "streaming.slo",
                    "subject": {
                        "type": "source_location",
                        "file": "contract",
                        "line": 1,
                        "col": 0,
                        "symbol": "transport-slo",
                    },
                    "attrs": {
                        "name": "transport-slo",
                        "metric": "lag",
                        "operator": "lte",
                        "unit": "records",
                        "window": "5m",
                        "source": "kafka",
                    },
                    "measures": {"target": 50},
                }
            ]
        ),
        encoding="utf-8",
    )
    kafka.write_text(
        json.dumps(
            [
                {
                    "kind": "kafka.lag",
                    "subject": {"type": "source_location", "file": "kafka", "line": 1, "col": 0},
                    "attrs": {"group": "orders-group", "topic": "orders", "observed_at": timestamp},
                    "measures": {"partition": 0, "lag": value},
                }
                for value, timestamp in (
                    (40, "2026-10-02T12:00:00Z"),
                    (50, "2026-10-02T12:05:00Z"),
                    (45, "2026-10-02T12:10:00Z"),
                )
            ]
        ),
        encoding="utf-8",
    )
    args = {
        "facts_paths": [str(contract), str(kafka)],
        "mode": "slo",
        "slo_name": "transport-slo",
        "transport_key": "orders-group",
        "limit": 20,
    }
    expected = analyze_streaming_composition(**args)
    actual = call_tool("sparkforge_analyze_streaming_composition", args)
    # `_trust` e aditivo em todo resultado de call_tool (FASE 3); o contrato
    # do envelope e comparado sem ele, e o formato e travado em
    # tests/test_runtime_convergence_trust.py.
    actual.pop("_trust", None)
    assert actual == expected
    assert any(
        item["kind"] == "streaming.slo.evaluation" and item["attrs"]["status"] == "met"
        for item in expected["items"]
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge_aws.adapters.cli",
            "analyze",
            "streaming-composition",
            "--facts",
            str(contract),
            "--facts",
            str(kafka),
            "--mode",
            "slo",
            "--slo-name",
            "transport-slo",
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


def test_sink_slo_cli_and_mcp_envelopes_match(tmp_path: Path):
    contract = tmp_path / "contract-sink.json"
    progress = tmp_path / "progress-sink.json"
    contract.write_text(
        json.dumps(
            [
                {
                    "kind": "streaming.slo",
                    "subject": {
                        "type": "source_location",
                        "file": "contract",
                        "line": 1,
                        "col": 0,
                        "symbol": "sink-output",
                    },
                    "attrs": {
                        "name": "sink-output",
                        "metric": "num_output_rows",
                        "operator": "gte",
                        "unit": "rows",
                        "window": "5m",
                        "source": "streaming_sink",
                        "sink_name": "iceberg-orders",
                    },
                    "measures": {"target": 90},
                }
            ]
        ),
        encoding="utf-8",
    )
    progress.write_text(
        json.dumps(
            [
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 1, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:00:00Z"},
                    "measures": {"batch_id": 1},
                },
                {
                    "kind": "streaming.progress.sink",
                    "subject": {"type": "source_location", "file": "progress", "line": 1, "col": 0},
                    "attrs": {"description": "iceberg-orders"},
                    "measures": {"batch_id": 1, "num_output_rows": 100},
                },
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 2, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:05:00Z"},
                    "measures": {"batch_id": 2},
                },
                {
                    "kind": "streaming.progress.sink",
                    "subject": {"type": "source_location", "file": "progress", "line": 2, "col": 0},
                    "attrs": {"description": "iceberg-orders"},
                    "measures": {"batch_id": 2, "num_output_rows": 90},
                },
                {
                    "kind": "streaming.progress.batch",
                    "subject": {"type": "source_location", "file": "progress", "line": 3, "col": 0},
                    "attrs": {"query_name": "orders-query", "timestamp": "2026-10-02T12:10:00Z"},
                    "measures": {"batch_id": 3},
                },
                {
                    "kind": "streaming.progress.sink",
                    "subject": {"type": "source_location", "file": "progress", "line": 3, "col": 0},
                    "attrs": {"description": "iceberg-orders"},
                    "measures": {"batch_id": 3, "num_output_rows": 110},
                },
            ]
        ),
        encoding="utf-8",
    )
    args = {
        "facts_paths": [str(contract), str(progress)],
        "mode": "slo",
        "slo_name": "sink-output",
        "query_name": "orders-query",
        "limit": 20,
    }
    expected = analyze_streaming_composition(**args)
    actual = call_tool("sparkforge_analyze_streaming_composition", args)
    # `_trust` e aditivo em todo resultado de call_tool (FASE 3); o contrato
    # do envelope e comparado sem ele, e o formato e travado em
    # tests/test_runtime_convergence_trust.py.
    actual.pop("_trust", None)
    assert actual == expected
    assert any(
        item["kind"] == "streaming.slo.evaluation"
        and item["attrs"]["observation_source"] == "streaming.progress.sink"
        for item in expected["items"]
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge_aws.adapters.cli",
            "analyze",
            "streaming-composition",
            "--facts",
            str(contract),
            "--facts",
            str(progress),
            "--mode",
            "slo",
            "--slo-name",
            "sink-output",
            "--query-name",
            "orders-query",
            "--limit",
            "20",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == expected
