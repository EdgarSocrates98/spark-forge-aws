import json
from pathlib import Path

from sparkforge_aws.adapters.cli import main
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.lakeformation.architecture import analyze_architecture
from sparkforge_aws.lakeformation.capabilities import capability, load_matrix
from sparkforge_aws.lakeformation.catalog_routing import route_catalogs


def _golden_input(**overrides):
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
        "access_model": "fgac",
        "operation": "merge",
        "api": "spark_sql",
        "cross_account": True,
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
        "source_operation": "read",
        "target_operation": "merge",
    }
    payload.update(overrides)
    return payload


def test_routing_preserves_account_ownership_dimensions():
    result = route_catalogs(_golden_input())
    assert result["status"] == "ok"
    assert result["dimensions"] == {
        "job_account_id": "222222222222",
        "local_account_id": "222222222222",
        "source_account_id": "111111111111",
        "target_account_id": "222222222222",
        "source_catalog_owner_account_id": "111111111111",
        "target_catalog_owner_account_id": "222222222222",
    }
    assert result["catalogs"]["source"]["glue_id"] == "111111111111"


def test_routing_does_not_alias_glue_id_and_account_id():
    payload = _golden_input(
        source_catalog={
            "name": "producer_catalog",
            "owner_account_id": "111111111111",
            "glue_id": "111111111111",
            "glue_account_id": "222222222222",
        }
    )
    result = route_catalogs(payload)
    assert result["status"] == "unresolved"
    assert "glue_id_account_id_diverge" in result["required_verification"]


def test_glue4_dynamicframe_to_glue5_fgac_is_migration():
    result = analyze_architecture(
        _golden_input(
            runtime="4.0",
            source_format="parquet",
            target_format="parquet",
            access_model="fgac",
            operation="read",
            api="dynamicframe",
            cross_account=False,
            migration={"from_runtime": "4.0", "to_runtime": "5.1"},
        )
    )
    assert result["decision"]["access_model"] == "migration_required"
    assert any(check["code"] == "GLUE-LF-MIGRATION" for check in result["checks"])
    assert not any("spark.read.parquet" in action for action in result["decision"]["rollback"])


def test_glue_access_model_is_version_and_operation_aware():
    fgac = analyze_architecture(_golden_input())
    assert fgac["decision"]["capability"] == "version_dependent"
    both = analyze_architecture(_golden_input(access_model="both"))
    assert both["status"] == "blocked"
    assert any(check["code"] == "LF-MODE-CONFLICT" for check in both["checks"])


def test_emr_release_capabilities_are_version_aware():
    fgac = analyze_architecture(
        _golden_input(
            engine="emr_ec2",
            runtime="6.15.0",
            access_model="fgac",
            operation="read",
            source_operation="read",
            target_operation="read",
        )
    )
    fta = analyze_architecture(
        _golden_input(
            engine="emr_ec2",
            runtime="7.8.0",
            access_model="fta",
            operation="read",
            source_operation="read",
            target_operation="read",
        )
    )
    unknown = analyze_architecture(
        _golden_input(
            engine="emr_serverless",
            runtime="7.1",
            access_model="fta",
            operation="read",
            source_operation="read",
            target_operation="read",
        )
    )
    assert fgac["decision"]["capability"] == "supported"
    assert fta["decision"]["capability"] == "supported"
    assert unknown["status"] == "unresolved"
    assert "capability_not_declared" in unknown["decision"]["required_verification"]


def test_read_and_write_authorization_are_separate():
    result = analyze_architecture(
        _golden_input(
            access_model="fta",
            operation="write",
            target_operation="write",
            evidence={
                "ram": "accepted",
                "resource_link": "present",
                "iam_get_data_access": "allowed",
                "lakeformation_permission": "select",
                "registered_location": True,
                "application_integration": "enabled",
                "filesystem": "emrfs",
            },
        )
    )
    write_check = next(
        check for check in result["checks"] if check["code"] == "LF-WRITE-PERMISSION"
    )
    assert write_check["status"] == "blocked"
    assert "ALL" in write_check["required_verification"]


def test_credential_vending_preflight_is_layered():
    result = analyze_architecture(
        _golden_input(
            access_model="fta",
            operation="read",
            evidence={
                "ram": "accepted",
                "resource_link": "present",
                "iam_get_data_access": "denied",
                "lakeformation_permission": "all",
                "registered_location": True,
                "application_integration": "enabled",
                "filesystem": "emrfs",
            },
        )
    )
    check = next(check for check in result["checks"] if check["code"] == "IAM-GETDATAACCESS")
    assert check["status"] == "blocked"
    assert all("s3:*" not in action for action in result["decision"]["inferred"])


def test_cross_account_governance_requires_independent_evidence():
    result = analyze_architecture(
        _golden_input(
            evidence={
                "ram": "pending",
                "resource_link": "absent",
                "iam_get_data_access": "unknown",
                "lakeformation_permission": "unknown",
                "registered_location": None,
                "application_integration": "unknown",
                "filesystem": "unknown",
            }
        )
    )
    assert result["status"] == "unresolved"
    assert {"ram", "resource_link", "iam_get_data_access"} <= set(
        result["decision"]["required_verification"]
    )


def test_golden_path_glue51_cross_account_iceberg():
    result = analyze_architecture(_golden_input())
    assert result["status"] == "consistent"
    assert result["routing"]["catalogs"]["source"]["owner_account_id"] == "111111111111"
    assert result["routing"]["catalogs"]["target"]["owner_account_id"] == "222222222222"
    assert result["decision"]["access_model"] == "FGAC"


def test_negative_scenarios_fail_closed():
    dynamic = analyze_architecture(
        _golden_input(runtime="5.1", api="dynamicframe", operation="read")
    )
    direct_s3 = analyze_architecture(
        _golden_input(api="direct_s3", access_model="fta", operation="read")
    )
    emr_both = analyze_architecture(
        _golden_input(engine="emr_ec2", runtime="7.8.0", access_model="both")
    )
    assert dynamic["status"] in {"blocked", "unresolved"}
    assert direct_s3["status"] in {"blocked", "unresolved"}
    assert emr_both["status"] == "blocked"
    outputs = str([dynamic, direct_s3, emr_both])
    assert "add S3" not in outputs


def test_capability_matrix_is_source_backed():
    matrix = load_matrix()
    assert {"glue", "emr_ec2", "emr_serverless"} <= set(matrix["engines"])
    for row in matrix["capabilities"]:
        assert row["status"] in {
            "supported",
            "limited",
            "read_only",
            "version_dependent",
            "not_supported",
            "unknown",
        }
        if row["status"] != "unknown":
            assert row["source"] and row["last_verified"] and row["limitations"]
    assert capability("glue", "5.1", "fgac", "iceberg", "merge")["status"] in {
        "supported",
        "limited",
        "version_dependent",
    }
    assert capability("emr_ec2", "7.8.0", "fta", "iceberg", "read")["status"] == "supported"


def test_cli_and_mcp_architecture_parity(tmp_path, capsys):
    payload = _golden_input()
    input_path = tmp_path / "architecture.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["lakeformation", "architect", "--input", str(input_path)]) == 0
    cli_result = json.loads(capsys.readouterr().out)
    mcp_result = call_tool("sparkforge_aws_lakeformation_architect", {"payload": payload})

    # `_trust` e aditivo de call_tool (FASE 3); formato travado em
    # tests/test_runtime_convergence_trust.py
    mcp_result.pop("_trust", None)
    assert cli_result == mcp_result


def test_architecture_docs_and_vnext_are_anchored():
    root = Path(__file__).resolve().parents[1]
    knowledge = (root / "knowledge/lakeformation/architecture.md").read_text(encoding="utf-8")
    assert "security-access-control-fta.html" in knowledge
    assert "emr-lf-enable.html" in knowledge
    assert "cross-data-sharing-lf.html" in knowledge
    assert "required_verification" in knowledge

    skill = (root / "skills/lakeformation-architecture/SKILL.md").read_text(encoding="utf-8")
    assert "sparkforge-aws lakeformation architect" in skill
    assert "Não faz" in skill

    for path in (
        "agents/sf-lake-formation-specialist.md",
        "agents/sf-runtime-specialist.md",
    ):
        assert "lakeformation-architecture" in (root / path).read_text(encoding="utf-8")

    guide = (root / "docs/guia/usos/lake-formation-e-acesso.md").read_text(encoding="utf-8")
    assert "lakeformation architect" in guide
    assert "sparkforge_aws_lakeformation_architect" in guide

    for path in (
        "docs/vnext/ARCHITECTURE.md",
        "docs/vnext/CAPABILITY-MATRIX.md",
        "docs/vnext/KNOWLEDGE-MAP.md",
    ):
        assert "knowledge/lakeformation/capability-matrix.yaml" in (
            root / path
        ).read_text(encoding="utf-8")

    claims = (root / "docs/claims.lock.json").read_text(encoding="utf-8")
    assert "lakeformation" in claims.lower()
