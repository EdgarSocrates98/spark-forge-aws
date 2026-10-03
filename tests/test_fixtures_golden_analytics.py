"""Golden coverage for offline analytics artifacts."""

from __future__ import annotations

from pathlib import Path

from sparkforge.analytics.dbt import analyze_dbt_artifacts
from sparkforge.analytics.duckdb import analyze_duckdb_microscope

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "analytics"


def test_dbt_bundle_is_normalized_from_all_three_artifacts():
    payload = analyze_dbt_artifacts(FIXTURES / "dbt")
    report = payload["dbt"]
    assert report["project"] == "synthetic_analytics"
    assert report["resources"]
    assert report["catalog_nodes"]
    assert report["run_results"]
    assert report["unresolved"] == []
    assert len(report["fingerprint"]) == 64


def test_duckdb_microscope_is_read_only_and_deterministic():
    payload = analyze_duckdb_microscope(FIXTURES / "duckdb" / "microscope.yaml")
    report = payload["duckdb"]
    assert report["read_only"] is True
    assert report["objects"]
    assert report["queries"]
    assert all(query["read_only"] for query in report["queries"])
    assert len(report["fingerprint"]) == 64
