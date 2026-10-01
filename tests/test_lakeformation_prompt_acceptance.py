from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.lakeformation.architecture import analyze_architecture


def _payload(**overrides):
    payload = {
        "engine": "glue",
        "runtime": "5.1",
        "job_account_id": "222222222222",
        "local_account_id": "222222222222",
        "source_account_id": "111111111111",
        "target_account_id": "222222222222",
        "source_catalog": {
            "name": "producer_catalog",
            "owner_account_id": "111111111111",
            "glue_id": "111111111111",
            "glue_account_id": "111111111111",
        },
        "target_catalog": {
            "name": "local_catalog",
            "owner_account_id": "222222222222",
            "glue_id": "222222222222",
            "glue_account_id": "222222222222",
        },
        "source_format": "iceberg",
        "target_format": "iceberg",
        "source_operation": "read",
        "target_operation": "merge",
        "access_model": "fgac",
        "operation": "read",
        "api": "spark_sql",
        "cross_account": True,
        "cross_account_resolution": {
            "mode": "resource_link",
            "service": "glue_etl",
        },
        "evidence": {
            "ram": "accepted",
            "ram_share_status": "active",
            "ram_association": "associated",
            "cross_account_version": 4,
            "resource_link": "present",
            "iam_get_data_access": "allowed",
            "lakeformation_permission": "all",
            "registered_location": True,
            "application_integration": "enabled",
            "filesystem": "s3a",
            "capability_verification": "accepted",
            "catalog_metadata": "allowed",
            "kms": "allowed",
            "runtime_role": "arn:aws:iam::222222222222:role/job",
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("from_engine", "from_runtime", "to_engine", "to_runtime", "from_model", "to_model"),
    [
        ("glue", "4.0", "glue", "5.0", None, None),
        ("glue", "4.0", "glue", "5.1", None, None),
        ("glue", "5.0", "glue", "5.1", None, None),
        ("glue", "5.1", "emr_ec2", "7.12", None, None),
        ("emr_ec2", "7.8", "emr_ec2", "7.12", None, None),
        ("glue", "5.1", "glue", "5.1", "fgac", "fta"),
        ("glue", "5.1", "glue", "5.1", "fta", "fgac"),
    ],
)
def test_migration_report_covers_declared_transition_families(
    from_engine, from_runtime, to_engine, to_runtime, from_model, to_model
):
    migration = {
        "from_engine": from_engine,
        "from_runtime": from_runtime,
        "to_engine": to_engine,
        "to_runtime": to_runtime,
    }
    if from_model:
        migration.update({"from_access_model": from_model, "to_access_model": to_model})
    result = analyze_architecture(_payload(migration=migration))
    report = result["review"]["migration"]
    assert report["transition_family"] != "unknown"
    assert report["testing_plan"]
    assert report["rollback_plan"]
    assert report["security_changes"]
    assert all("%" not in item for item in report["cost_changes"])


def test_access_graph_and_cross_account_observability_are_explicit():
    result = analyze_architecture(
        _payload(
            source_format="iceberg",
            target_format="iceberg",
            observability={
                "cloudtrail": {
                    "consumer": {"status": "present", "events": ["GetTable"]},
                    "producer": {"status": "present", "events": ["GetDataAccess"]},
                },
                "glue_logs": "present",
                "spark_logs": "present",
                "lakeformation_audit": "present",
                "ram_state": "present",
            },
        )
    )
    explain = result["review"]["access_explain"]
    nodes = {node["name"] if isinstance(node, dict) else node for node in explain["nodes"]}
    assert {"job", "role", "glue_catalog", "lake_formation", "s3", "kms"} <= nodes
    assert {"spark", "iceberg", "glue_catalog", "credential_vending", "s3fileio"} <= nodes
    iceberg_path = next(path for path in explain["paths"] if path["name"] == "iceberg_data")
    assert iceberg_path["nodes"] == [
        "spark",
        "iceberg",
        "glue_catalog",
        "lake_formation",
        "credential_vending",
        "s3fileio",
    ]
    cloudtrail = result["review"]["observability"]["cloudtrail"]
    assert cloudtrail["consumer"]["status"] == "present"
    assert cloudtrail["producer"]["status"] == "present"


def test_preflight_is_layered_and_route_aware():
    explicit = _payload(
        cross_account_resolution={
            "mode": "explicit_catalog_id",
            "catalog_id": "111111111111",
            "service": "glue_etl",
        },
        evidence={
            **_payload()["evidence"],
            "resource_link": "absent",
            "cross_account_version": 4,
        },
    )
    result = analyze_architecture(explicit)
    preflight = {item["code"]: item for item in result["review"]["preflight"]}
    assert "RESOURCE-LINK" not in preflight
    assert preflight["RAM-SHARE"]["status"] == "pass"
    assert preflight["RAM-ASSOCIATION"]["status"] == "pass"
    assert preflight["CROSS-ACCOUNT-VERSION"]["status"] == "pass"

    missing = analyze_architecture(
        _payload(
            cross_account_resolution={
                "mode": "explicit_catalog_id",
                "catalog_id": "111111111111",
                "service": "glue_etl",
            },
            evidence={**_payload()["evidence"], "cross_account_version": None},
        )
    )
    assert "cross_account_version" in missing["decision"]["required_verification"]
    assert any(
        item["code"] == "CROSS-ACCOUNT-VERSION" and item["status"] == "unresolved"
        for item in missing["review"]["preflight"]
    )


def test_performance_finops_preserves_measurement_boundaries():
    result = analyze_architecture(_payload())
    dimensions = result["review"]["performance_finops"]["dimensions"]
    assert {
        "security_requirement",
        "latency",
        "resource_overhead",
        "worker_requirements",
        "runtime_duration",
        "dpu_seconds",
        "cost",
    } <= set(dimensions)
    assert all(value["status"] == "conditional" for value in dimensions.values())
    measured = analyze_architecture(
        _payload(
            benchmark={
                "duration_seconds": 120,
                "workers": 4,
                "dpu_seconds": 480,
                "cost_basis": "glue_dpu_price_us_east_1",
            }
        )
    )
    observed = measured["review"]["performance_finops"]["observed_measurements"]
    assert {item["metric"] for item in observed} >= {
        "duration_seconds",
        "workers",
        "dpu_seconds",
        "cost_basis",
    }


def test_decision_graph_is_bounded_and_version_aware():
    result = analyze_architecture(_payload())
    graph = result["review"]["decision_graph"]
    assert graph["nodes"]
    assert graph["edges"]
    assert len(graph["nodes"]) <= 16
    assert {"engine", "runtime", "access_model", "format", "operation"} <= set(graph["dimensions"])
    emr = analyze_architecture(_payload(engine="emr_ec2", runtime="7.12", access_model="fta"))
    assert not any(
        "glue/lakeformation-fgac" in ref
        for ref in emr["review"]["progressive_disclosure"]["knowledge_refs"]
    )


def test_prompt_scenario_matrix_has_positive_and_negative_cases():
    cases = [
        (
            "glue51_parquet_local_fgac_read",
            {
                "source_format": "parquet",
                "target_format": "parquet",
                "source_operation": "read",
                "target_operation": "read",
                "operation": "read",
                "cross_account": False,
            },
            "consistent",
        ),
        (
            "glue51_parquet_cross_fgac_read",
            {"source_format": "parquet", "cross_account": True},
            "consistent",
        ),
        (
            "glue51_iceberg_local_fgac_read",
            {"cross_account": False, "source_operation": "read", "target_operation": "read"},
            "consistent",
        ),
        (
            "glue51_iceberg_cross_fgac_read",
            {"cross_account": True, "source_operation": "read", "target_operation": "read"},
            "consistent",
        ),
        (
            "glue51_iceberg_fgac_write",
            {
                "cross_account": False,
                "source_operation": "read",
                "target_operation": "write",
                "operation": "write",
                "source_api": "spark_sql",
                "target_api": "dataframe",
            },
            "consistent",
        ),
        (
            "source_cross_target_local",
            {"cross_account": True, "target_account_id": "222222222222"},
            "consistent",
        ),
        (
            "wrong_glue_id",
            {"source_catalog": {**_payload()["source_catalog"], "glue_id": "999999999999"}},
            "unresolved",
        ),
        (
            "wrong_glue_account_id",
            {"source_catalog": {**_payload()["source_catalog"], "glue_account_id": "999999999999"}},
            "unresolved",
        ),
        (
            "missing_get_data_access",
            {
                "access_model": "fta",
                "evidence": {**_payload()["evidence"], "iam_get_data_access": "denied"},
            },
            "blocked",
        ),
        (
            "ram_not_accepted",
            {"evidence": {**_payload()["evidence"], "ram": "pending"}},
            "unresolved",
        ),
        (
            "lf_select_missing",
            {"evidence": {**_payload()["evidence"], "lakeformation_permission": "absent"}},
            "unresolved",
        ),
        ("kms_denied", {"evidence": {**_payload()["evidence"], "kms": "denied"}}, "blocked"),
        (
            "fta_hive_read",
            {
                "access_model": "fta",
                "source_format": "hive",
                "target_format": "hive",
                "source_operation": "read",
                "target_operation": "read",
            },
            "unresolved",
        ),
        (
            "fta_iceberg_read",
            {"access_model": "fta", "source_operation": "read", "target_operation": "read"},
            "unresolved",
        ),
        ("dynamicframe_fta", {"access_model": "fta", "api": "dynamicframe"}, "unresolved"),
        (
            "emr_fgac",
            {
                "engine": "emr_ec2",
                "runtime": "6.15",
                "cross_account": False,
                "source_operation": "read",
                "target_operation": "read",
            },
            "consistent",
        ),
        (
            "emr_fta",
            {
                "engine": "emr_ec2",
                "runtime": "7.8",
                "access_model": "fta",
                "cross_account": False,
                "source_operation": "read",
                "target_operation": "read",
            },
            "consistent",
        ),
        (
            "emr_conflict",
            {"engine": "emr_ec2", "runtime": "7.8", "access_model": "both", "cross_account": False},
            "blocked",
        ),
        (
            "emr_iceberg_fgac",
            {
                "engine": "emr_ec2",
                "runtime": "6.15",
                "cross_account": False,
                "source_operation": "read",
                "target_operation": "read",
            },
            "consistent",
        ),
        (
            "emr_iceberg_fta",
            {
                "engine": "emr_ec2",
                "runtime": "7.8",
                "access_model": "fta",
                "cross_account": False,
                "source_operation": "read",
                "target_operation": "read",
            },
            "consistent",
        ),
        (
            "emr_cross_resource_link",
            {
                "engine": "emr_ec2",
                "runtime": "7.8",
                "access_model": "fta",
                "cross_account_resolution": {"mode": "resource_link", "service": "emr"},
            },
            "unresolved",
        ),
        (
            "credential_vending_failure",
            {
                "errors": [
                    {
                        "message": "GetTemporaryCredentialsForTableV2 AccessDeniedException",
                        "source": {"file": "driver.log", "line": 10},
                    }
                ]
            },
            "blocked",
        ),
    ]
    assert len(cases) == 22
    assert {expected for _, _, expected in cases} >= {"consistent", "unresolved", "blocked"}
    for name, overrides, expected in cases:
        result = analyze_architecture(_payload(**overrides))
        assert result["status"] == expected, name


def test_prompt_acceptance_audit_is_complete():
    root = Path(__file__).resolve().parents[1]
    audit = (
        root / "docs/sdd/LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION/prompt-acceptance-audit.md"
    ).read_text(encoding="utf-8")
    assert all(f"| {number} |" in audit for number in range(1, 27))
    for path in (
        "knowledge/lakeformation/operational-closure.md",
        "docs/guia/usos/lake-formation-operacional.md",
        "skills/lakeformation-architecture/SKILL.md",
        "docs/vnext/ARCHITECTURE.md",
        "docs/vnext/CAPABILITY-MATRIX.md",
        "docs/vnext/KNOWLEDGE-MAP.md",
    ):
        text = (root / path).read_text(encoding="utf-8").lower()
        assert "decision graph" in text or "acceptance" in text or "cloudtrail" in text
