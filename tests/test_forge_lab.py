"""Contract tests for the declarative Forge Lab."""

from __future__ import annotations

from pathlib import Path

from sparkforge.lab.spec import FORGE_LAB_COMPONENTS, FORGE_LAB_SCENARIOS, analyze_forge_lab, load_forge_lab


FIXTURE = Path(__file__).parents[1] / "labs" / "forge-lab" / "lab.yaml"


def test_forge_lab_validates_topology_and_scenarios() -> None:
    spec = load_forge_lab(FIXTURE)

    assert {item["kind"] for item in spec.components} == FORGE_LAB_COMPONENTS
    assert {item["id"] for item in spec.scenarios} == FORGE_LAB_SCENARIOS
    assert spec.unresolved == ()
    assert spec.topology_order()[0] == "kafka" or spec.topology_order()[0] == "minio"
    assert all(item["requires_confirmation"] for item in spec.scenarios)


def test_forge_lab_analysis_is_offline_and_structured() -> None:
    payload = analyze_forge_lab(FIXTURE)

    assert payload["lab"]["mode"] == "offline_spec_only"
    assert payload["lab"]["readiness"].startswith("unresolved_until_operator")
    assert payload["lab"]["fingerprint"]
    assert {item["id"] for item in payload["lab"]["components"]} >= {"kafka", "flink", "iceberg_rest"}


def test_forge_lab_docs_match_declared_scenarios() -> None:
    readme = FIXTURE.parent / "README.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    for scenario in FORGE_LAB_SCENARIOS:
        assert scenario in text
