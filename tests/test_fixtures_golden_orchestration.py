"""Golden coverage for offline orchestration control-plane artifacts."""

from __future__ import annotations

from pathlib import Path

from sparkforge.orchestration.topology import analyze_orchestration

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "orchestration"


def test_control_plane_normalizes_all_declared_orchestrators():
    report = analyze_orchestration(FIXTURES / "control-plane.yaml")["orchestration"]
    assert report["topology"] == "synthetic-control-plane"
    assert {item["kind"] for item in report["orchestrators"]} == {
        "airflow",
        "dagster",
        "step_functions",
        "controlm",
    }
    assert report["workflows"]
    assert len(report["fingerprint"]) == 64
