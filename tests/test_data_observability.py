"""Contract tests for offline data observability/SRE evaluation."""

from __future__ import annotations

from pathlib import Path

from sparkforge_aws.adapters import _core
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.observability.sre import load_data_observability

FIXTURE = Path(__file__).parents[1] / "fixtures" / "observability" / "sre.yaml"


def test_observability_evaluates_slos_and_error_budget() -> None:
    report = load_data_observability(FIXTURE)
    by_id = {item["id"]: item for item in report.slo_reports}

    assert by_id["orders_freshness"]["status"] == "breached"
    assert by_id["orders_freshness"]["error_budget_consumed_fraction"] > 0
    assert by_id["orders_completeness"]["status"] == "met"
    assert by_id["orders_latency_missing"]["status"] == "unresolved"
    assert {item["code"] for item in report.unresolved} >= {
        "slo_measurement_unresolved",
        "incident_mttr_unresolved",
    }


def test_observability_preserves_incidents_dependencies_and_blast_radius() -> None:
    report = load_data_observability(FIXTURE)

    resolved = next(item for item in report.incidents if item["id"] == "inc-2026-10-02-001")
    assert resolved["mttr_seconds"] == 2700
    assert any(item["status"] == "degraded" for item in report.dependencies)
    assert report.blast_radius[0]["root"] == "postgres.orders"


def test_observability_surfaces_share_contract() -> None:
    cli = _core.analyze_data_observability(FIXTURE)
    mcp = call_tool("sparkforge_aws_analyze_data_observability", {"path": str(FIXTURE)})

    assert cli["observability"]["fingerprint"] == mcp["observability"]["fingerprint"]


def test_observability_document_sets_offline_boundary() -> None:
    document = Path(__file__).parents[1] / "docs" / "knowledge" / "data-observability-sre.md"
    assert "offline" in document.read_text(encoding="utf-8").lower()
