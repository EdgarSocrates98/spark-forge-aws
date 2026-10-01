import json
from pathlib import Path

from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import call_tool
from sparkforge.lakeformation.architecture import analyze_architecture
from sparkforge.lakeformation.capabilities import capability, load_matrix
from sparkforge.lakeformation.catalog_routing import route_catalogs


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
            "resource_link": "present",
            "iam_get_data_access": "allowed",
            "lakeformation_permission": "all",
            "registered_location": True,
            "application_integration": "enabled",
            "filesystem": "s3a",
            "capability_verification": "accepted",
        },
    }
    payload.update(overrides)
    return payload


def test_capability_statuses_are_enforced():
    not_supported = analyze_architecture(
        _payload(
            engine="emr_ec2",
            runtime="6.15",
            access_model="fgac",
            source_format="iceberg",
            target_format="iceberg",
            source_operation="read",
            target_operation="write",
            operation="write",
            cross_account=False,
            evidence={"lakeformation_permission": "all", "capability_verification": "accepted"},
        )
    )
    assert not_supported["status"] == "blocked"
    assert any(check["code"] == "CAPABILITY-NOT-SUPPORTED" for check in not_supported["checks"])

    read_only = analyze_architecture(
        _payload(
            engine="emr_ec2",
            runtime="6.15",
            access_model="fgac",
            source_format="hudi",
            target_format="hudi",
            source_operation="read",
            target_operation="write",
            operation="write",
            cross_account=False,
            evidence={"lakeformation_permission": "all", "capability_verification": "accepted"},
        )
    )
    assert read_only["status"] == "blocked"
    assert any(check["code"] == "CAPABILITY-READ-ONLY" for check in read_only["checks"])

    limited = analyze_architecture(
        _payload(
            engine="emr_ec2",
            runtime="7.8",
            access_model="fta",
            source_format="iceberg",
            target_format="iceberg",
            source_operation="read",
            target_operation="write",
            operation="write",
            cross_account=False,
            evidence={
                "lakeformation_permission": "all",
                "iam_get_data_access": "allowed",
                "application_integration": "enabled",
                "capability_verification": None,
            },
        )
    )
    assert limited["status"] == "unresolved"
    assert "capability_specific_verification" in limited["decision"]["required_verification"]

    version_dependent = analyze_architecture(
        _payload(evidence={**_payload()["evidence"], "capability_verification": None})
    )
    assert version_dependent["status"] == "unresolved"
    assert "capability_specific_verification" in version_dependent["decision"][
        "required_verification"
    ]


def test_source_and_target_are_evaluated_independently():
    result = analyze_architecture(
        _payload(
            source_format="parquet",
            target_format="iceberg",
            operation="read",
            source_operation="read",
            target_operation="merge",
        )
    )
    assert result["decision"]["source_decision"]["format"] == "parquet"
    assert result["decision"]["source_decision"]["operation"] == "read"
    assert result["decision"]["target_decision"]["format"] == "iceberg"
    assert result["decision"]["target_decision"]["operation"] == "merge"
    assert result["decision"]["source_decision"]["capability"] == "supported"
    assert result["decision"]["target_decision"]["capability"] == "version_dependent"


def test_cross_account_resolution_modes():
    explicit_catalog_id = analyze_architecture(
        _payload(
            cross_account_resolution={
                "mode": "explicit_catalog_id",
                "catalog_id": "111111111111",
                "service": "glue_etl",
            },
            evidence={
                "ram": "accepted",
                "iam_get_data_access": "allowed",
                "lakeformation_permission": "all",
                "registered_location": True,
                "capability_verification": "accepted",
            },
        )
    )
    assert explicit_catalog_id["status"] == "consistent"
    assert explicit_catalog_id["review"]["cross_account_resolution"]["mode"] == (
        "explicit_catalog_id"
    )
    assert "resource_link" not in explicit_catalog_id["decision"]["required_verification"]

    missing_route = analyze_architecture(
        _payload(
            cross_account_resolution=None,
            evidence={
                "ram": "accepted",
                "iam_get_data_access": "allowed",
                "lakeformation_permission": "all",
                "registered_location": True,
                "capability_verification": "accepted",
            },
        )
    )
    assert missing_route["status"] == "unresolved"
    assert "cross_account_resolution" in missing_route["decision"]["required_verification"]


def test_hybrid_access_is_governance_aware():
    complete = analyze_architecture(
        _payload(
            access_governance_mode="hybrid",
            evidence={
                **_payload()["evidence"],
                "iam_allowed_principals": True,
                "hybrid_access_enabled": True,
                "hybrid_principal_opt_in": True,
                "cross_account_version": 4,
            },
        )
    )
    assert complete["status"] == "consistent"
    assert not any(check["code"] == "LF-IAMALLOWEDPRINCIPALS" for check in complete["checks"])
    assert complete["review"]["authorization"]["governance_mode"] == "hybrid"

    incomplete = analyze_architecture(
        _payload(
            access_governance_mode="hybrid",
            evidence={**_payload()["evidence"], "iam_allowed_principals": True},
        )
    )
    assert incomplete["status"] == "unresolved"
    assert "hybrid_principal_opt_in" in incomplete["decision"]["required_verification"]


def test_glue4_current_architecture_is_not_migration():
    current = analyze_architecture(
        _payload(
            runtime="4.0",
            source_format="parquet",
            target_format="parquet",
            source_operation="read",
            target_operation="read",
            operation="read",
            api="dynamicframe",
            cross_account=False,
            evidence={"capability_verification": "accepted"},
        )
    )
    assert current["decision"]["access_model"] == "FGAC"
    assert not any(check["code"] == "GLUE-LF-MIGRATION" for check in current["checks"])

    migration_payload = _payload(
        runtime="4.0",
        api="dynamicframe",
        cross_account=False,
        source_format="parquet",
        target_format="parquet",
        operation="read",
        source_operation="read",
        target_operation="read",
    )
    migration_payload["migration"] = {"from_runtime": "4.0", "to_runtime": "5.1"}
    migration = analyze_architecture(migration_payload)
    assert migration["decision"]["access_model"] == "migration_required"
    assert any(check["code"] == "GLUE-LF-MIGRATION" for check in migration["checks"])


def test_capability_matrix_expands_without_aliasing():
    matrix = load_matrix()
    assert len(matrix["capabilities"]) >= 40
    assert capability("glue", "5.1", "fgac", "parquet", "read", "dataframe")["status"] == (
        "supported"
    )
    assert capability("glue", "5.1", "fgac", "iceberg", "insert", "spark_sql")["status"] == (
        "version_dependent"
    )
    assert capability("emr_ec2", "7.12", "fta", "iceberg", "merge", "spark_sql")["status"] in {
        "supported",
        "limited",
        "version_dependent",
    }
    assert capability("emr_serverless", "7.12", "fta", "iceberg", "delete", "spark_sql")[
        "status"
    ] in {"supported", "version_dependent"}


def test_catalog_ids_have_semantic_comparisons():
    result = route_catalogs(
        _payload(
            source_catalog={
                "name": "producer_catalog",
                "owner_account_id": "111111111111",
                "glue_id": "111111111111",
                "glue_account_id": "222222222222",
                "expected_glue_account_id": "222222222222",
            }
        )
    )
    assert result["status"] == "ok"
    comparisons = {item["name"]: item for item in result["semantic_comparisons"]}
    assert comparisons["source.glue_id_vs_owner"]["status"] == "pass"
    assert comparisons["source.glue_account_id_vs_expected_context"]["status"] == "pass"
    assert "glue_id_account_id_diverge" not in result["required_verification"]


def test_improvement_contract_is_documented_and_parity_is_preserved(tmp_path, capsys):
    root = Path(__file__).resolve().parents[1]
    payload = _payload(source_format="parquet", target_format="iceberg")
    input_path = tmp_path / "architecture.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["lakeformation", "architect", "--input", str(input_path)]) == 0
    cli_result = json.loads(capsys.readouterr().out)
    assert cli_result == call_tool("sparkforge_lakeformation_architect", {"payload": payload})
    assert {"source_decision", "target_decision"} <= set(cli_result["decision"])
    for path in (
        "knowledge/lakeformation/fgac-fta-improvements.md",
        "skills/lakeformation-architecture/SKILL.md",
        "agents/sf-lake-formation-specialist.md",
        "agents/sf-runtime-specialist.md",
        "docs/vnext/ARCHITECTURE.md",
        "docs/vnext/CAPABILITY-MATRIX.md",
        "docs/vnext/KNOWLEDGE-MAP.md",
    ):
        text = (root / path).read_text(encoding="utf-8").lower()
        assert "source" in text and "target" in text
