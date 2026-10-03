"""Golden coverage for platform, catalog and ecosystem artifacts."""

from __future__ import annotations

from pathlib import Path

from sparkforge.catalog.contract import analyze_lakehouse_catalog
from sparkforge.platform.ecosystem import analyze_platform_ecosystem
from sparkforge.platform.graph import analyze_platform_graph

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "platform"


def test_platform_graph_preserves_declared_nodes_and_edges():
    report = analyze_platform_graph(FIXTURES / "graph.yaml")["graph"]
    assert report["platform"] == "synthetic-order-platform"
    assert report["nodes"]
    assert report["edges"]
    assert len(report["fingerprint"]) == 64


def test_platform_ecosystem_keeps_radar_optional():
    report = analyze_platform_ecosystem(FIXTURES / "ecosystem.yaml")["ecosystem"]
    assert report["systems"]
    assert {item["system_id"] for item in report["unresolved"]} == {
        "beam-radar",
        "datahub-radar",
        "openmetadata-radar",
    }
    assert len(report["fingerprint"]) == 64


def test_catalog_manifest_normalizes_catalog_kinds():
    report = analyze_lakehouse_catalog(FIXTURES / "catalog.yaml")["catalog"]
    assert report["topology"] == "synthetic-open-lakehouse"
    assert {item["kind"] for item in report["catalogs"]} == {
        "glue",
        "iceberg_rest",
        "polaris",
        "s3_tables",
        "lakeformation",
        "unity",
        "nessie",
    }
    assert len(report["fingerprint"]) == 64
