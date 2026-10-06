"""Contract tests for normalized orchestration topology."""

from __future__ import annotations

from pathlib import Path

from sparkforge_aws.adapters import _core
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.orchestration.topology import load_orchestration

FIXTURE = Path(__file__).parents[1] / "fixtures" / "orchestration" / "control-plane.yaml"


def test_orchestration_normalizes_reliability_controls() -> None:
    topology = load_orchestration(FIXTURE)

    assert {item["kind"] for item in topology.orchestrators} == {
        "airflow",
        "dagster",
        "step_functions",
        "controlm",
    }
    airflow = next(item for item in topology.workflows if item["id"] == "airflow.orders_ingest")
    assert airflow["retry"]["max_attempts"] == 3
    assert airflow["concurrency"]["pool"] == "streaming"
    assert airflow["backfill"]["enabled"] is True
    assert airflow["idempotent"] is True


def test_orchestration_preserves_unresolved_controls() -> None:
    topology = load_orchestration(FIXTURE)
    codes = {item["code"] for item in topology.unresolved}

    assert "workflow_dependency_unresolved" in codes
    assert "workflow_control_unresolved" in codes
    assert topology.unresolved


def test_orchestration_surfaces_share_contract() -> None:
    cli = _core.analyze_orchestration(FIXTURE)
    mcp = call_tool("sparkforge_analyze_orchestration", {"path": str(FIXTURE)})

    assert cli["orchestration"]["fingerprint"] == mcp["orchestration"]["fingerprint"]


def test_orchestration_knowledge_preserves_read_only_boundary() -> None:
    document = Path(__file__).parents[1] / "docs" / "knowledge" / "orchestration-control-plane.md"
    text = document.read_text(encoding="utf-8").lower()
    assert "does not trigger" in text or "não dispara" in text
