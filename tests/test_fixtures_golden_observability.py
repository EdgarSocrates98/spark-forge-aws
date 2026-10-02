"""Golden coverage for offline data-observability/SRE artifacts."""

from __future__ import annotations

from pathlib import Path

from sparkforge.observability.sre import analyze_data_observability


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "observability"


def test_sre_contract_preserves_unresolved_measurements():
    report = analyze_data_observability(FIXTURES / "sre.yaml")["observability"]
    assert report["service"] == "orders-platform"
    assert {item["id"] for item in report["slo_reports"]} == {
        "orders_completeness",
        "orders_freshness",
        "orders_lag",
        "orders_latency_missing",
    }
    assert any(item["code"] == "slo_measurement_unresolved" for item in report["unresolved"])
    assert len(report["fingerprint"]) == 64
