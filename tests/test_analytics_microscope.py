"""Contract tests for dbt artifacts and DuckDB microscope."""

from __future__ import annotations

from pathlib import Path

from sparkforge_aws.adapters import _core
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.analytics.dbt import load_dbt_artifacts
from sparkforge_aws.analytics.duckdb import load_duckdb_microscope

DBT_FIXTURE = Path(__file__).parents[1] / "fixtures" / "analytics" / "dbt"
DUCKDB_FIXTURE = Path(__file__).parents[1] / "fixtures" / "analytics" / "duckdb" / "microscope.yaml"


def test_dbt_artifacts_preserve_lineage_and_results() -> None:
    artifacts = load_dbt_artifacts(DBT_FIXTURE)

    model = next(
        item for item in artifacts.resources if item["unique_id"] == "model.synthetic.orders"
    )
    assert model["depends_on"] == ["source.synthetic.postgres.orders"]
    assert model["config"]["materialized"] == "incremental"
    assert len(artifacts.catalog_nodes) == 1
    assert {item["status"] for item in artifacts.run_results} == {"success"}
    assert artifacts.unresolved == ()


def test_duckdb_microscope_is_read_only_and_structured() -> None:
    microscope = load_duckdb_microscope(DUCKDB_FIXTURE)

    assert microscope.to_dict()["read_only"] is True
    assert len(microscope.objects) == 2
    assert microscope.objects[0]["stats"]["row_count"] == 1000
    assert microscope.queries[0]["read_only"] is True
    assert microscope.comparisons[0]["status"] == "declared"


def test_analytics_surfaces_share_contracts() -> None:
    dbt_cli = _core.analyze_dbt_artifacts(DBT_FIXTURE)
    dbt_mcp = call_tool("sparkforge_aws_analyze_dbt_artifacts", {"path": str(DBT_FIXTURE)})
    duckdb_cli = _core.analyze_duckdb_microscope(DUCKDB_FIXTURE)
    duckdb_mcp = call_tool(
        "sparkforge_aws_analyze_duckdb_microscope", {"path": str(DUCKDB_FIXTURE)}
    )

    assert dbt_cli["dbt"]["fingerprint"] == dbt_mcp["dbt"]["fingerprint"]
    assert duckdb_cli["duckdb"]["fingerprint"] == duckdb_mcp["duckdb"]["fingerprint"]
