"""Contract tests for open lakehouse catalog topology."""

from __future__ import annotations

from pathlib import Path

from sparkforge.adapters import _core
from sparkforge.adapters.tools import call_tool
from sparkforge.catalog.contract import analyze_lakehouse_catalog, load_lakehouse_catalog


FIXTURE = Path(__file__).parents[1] / "fixtures" / "platform" / "catalog.yaml"


def test_lakehouse_catalog_contract_is_deterministic() -> None:
    topology = load_lakehouse_catalog(FIXTURE)
    payload = analyze_lakehouse_catalog(FIXTURE)

    assert len(topology.catalogs) == 7
    assert len(topology.engines) == 5
    assert len(topology.bindings) == 3
    assert topology.unresolved == ()
    assert payload["catalog"]["fingerprint"] == topology.fingerprint
    assert all("password" not in str(item).lower() for item in topology.catalogs)


def test_lakehouse_catalog_cli_and_mcp_share_contract() -> None:
    cli = _core.analyze_lakehouse_catalog(FIXTURE)
    mcp = call_tool("sparkforge_analyze_lakehouse_catalog", {"path": str(FIXTURE)})

    assert mcp["catalog"]["fingerprint"] == cli["catalog"]["fingerprint"]
    assert mcp["catalog"]["bindings"] == cli["catalog"]["bindings"]


def test_lakehouse_catalog_knowledge_declares_unresolved_boundary() -> None:
    document = Path(__file__).parents[1] / "docs" / "knowledge" / "open-lakehouse-catalog.md"
    text = document.read_text(encoding="utf-8")

    assert "unresolved" in text
    assert "credential" in text.lower() or "credenciais" in text.lower()
