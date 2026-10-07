"""Contract tests for the serving/ingestion/AI/radar inventory."""

from __future__ import annotations

from pathlib import Path

from sparkforge_aws.adapters import _core
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.platform.ecosystem import load_platform_ecosystem

FIXTURE = Path(__file__).parents[1] / "fixtures" / "platform" / "ecosystem.yaml"


def test_ecosystem_normalizes_domains_and_reliability() -> None:
    ecosystem = load_platform_ecosystem(FIXTURE)

    assert {item["category"] for item in ecosystem.systems} == {
        "serving",
        "ingestion",
        "ai",
        "radar",
    }
    assert (
        next(item for item in ecosystem.reliability if item["system_id"] == "debezium")[
            "checkpointing"
        ]
        == "offsets"
    )
    assert any(item["relation"] == "serves" for item in ecosystem.integrations)


def test_ecosystem_preserves_unresolved_and_optional_radar() -> None:
    ecosystem = load_platform_ecosystem(FIXTURE)
    codes = {item["code"] for item in ecosystem.unresolved}

    assert "reliability_model_unresolved" in codes
    assert all(
        item.get("runtime_dependency") is False
        for item in ecosystem.integrations
        if item.get("role") == "radar"
    )


def test_ecosystem_surfaces_share_contract() -> None:
    cli = _core.analyze_platform_ecosystem(FIXTURE)
    mcp = call_tool("sparkforge_aws_analyze_platform_ecosystem", {"path": str(FIXTURE)})

    assert cli["ecosystem"]["fingerprint"] == mcp["ecosystem"]["fingerprint"]


def test_ecosystem_knowledge_marks_radar_optional() -> None:
    document = Path(__file__).parents[1] / "docs" / "knowledge" / "data-platform-ecosystem.md"
    text = document.read_text(encoding="utf-8").lower()
    assert "optional" in text or "opcional" in text
