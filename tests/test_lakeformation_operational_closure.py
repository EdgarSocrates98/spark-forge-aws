import json
from pathlib import Path

from sparkforge_aws.adapters.cli import main
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.lakeformation.architecture import analyze_architecture
from sparkforge_aws.lakeformation.capabilities import capability, load_matrix


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
        },
    }
    payload.update(overrides)
    return payload


def test_review_composes_code_iac_and_late_configuration():
    result = analyze_architecture(
        _payload(
            facts=[
                {
                    "kind": "pyspark.glue_context_init",
                    "subject": {"file": "job.py", "line": 5},
                    "attrs": {"api": "dynamicframe"},
                },
                {
                    "kind": "pyspark.read",
                    "subject": {"file": "job.py", "line": 20},
                    "attrs": {"api": "dynamicframe", "target": "catalog.db.table"},
                },
                {
                    "kind": "pyspark.conf_set",
                    "subject": {"file": "job.py", "line": 30},
                    "attrs": {
                        "key": "spark.sql.catalog.spark_catalog.glue.account-id",
                        "value": "111111111111",
                    },
                },
                {
                    "kind": "tf.spark_conf",
                    "subject": {"file": "main.tf", "line": 10},
                    "attrs": {
                        "key": "spark.sql.catalog.spark_catalog.glue.account-id",
                        "value": "111111111111",
                    },
                },
                {
                    "kind": "tf.attribute",
                    "subject": {"file": "main.tf", "line": 11},
                    "attrs": {"key": "--enable-lakeformation-fine-grained-access", "value": "true"},
                },
            ]
        )
    )
    review = result["review"]
    assert review["code_and_iac"]["status"] == "blocked"
    assert any(item["code"] == "DYNAMICFRAME-FGAC" for item in review["code_and_iac"]["findings"])
    assert any(item["code"] == "LATE-LF-CONFIG" for item in review["code_and_iac"]["findings"])
    assert any(item["kind"] == "tf.spark_conf" for item in review["code_and_iac"]["observed"])
    assert "spark_session_before_lf_config" in review["code_and_iac"]["required_verification"]


def test_review_explains_access_and_root_cause_layers():
    result = analyze_architecture(
        _payload(
            errors=[
                {
                    "message": "GetTemporaryCredentialsForTableV2 AccessDeniedException",
                    "source": {"file": "driver.log", "line": 77},
                }
            ],
            evidence={
                "ram": "accepted",
                "resource_link": "present",
                "iam_get_data_access": "denied",
                "lakeformation_permission": "select",
                "registered_location": True,
                "application_integration": "enabled",
                "filesystem": "s3a",
            },
        )
    )
    review = result["review"]
    assert review["access_explain"]["metadata_path"] == ["job", "glue_catalog", "lake_formation"]
    assert "credential_vending" in review["access_explain"]["data_path"]
    assert review["authorization"]["separation"] == "metadata_authorization != data_authorization"
    assert review["error_taxonomy"][0]["category"] == "credential_vending"
    assert review["error_taxonomy"][0]["evidence"] == ["driver.log:77"]
    root = review["root_cause"]
    assert root["status"] == "blocked"
    assert "credential_vending" in root["possible_layers"]
    assert "lakeformation:GetDataAccess" in root["required_proof"]
    assert all("Action: '*'" not in item for item in root["fix"])


def test_review_builds_version_aware_migration_report():
    result = analyze_architecture(
        _payload(
            migration={"from_runtime": "4.0", "to_runtime": "5.1"},
            source_format="parquet",
            target_format="iceberg",
            operation="merge",
        )
    )
    migration = result["review"]["migration"]
    assert migration["status"] == "required"
    assert any("DynamicFrame" in item for item in migration["breaking_changes"])
    assert migration["security_changes"]
    assert migration["testing_plan"] and migration["rollback_plan"]
    assert all("%" not in item for item in migration["cost_changes"])


def test_matrix_closure_keeps_format_and_source_boundaries():
    matrix = load_matrix()
    assert {"glue", "emr_ec2", "emr_serverless"} <= set(matrix["engines"])
    formats = {row["format"] for row in matrix["capabilities"]}
    assert {"hive", "parquet", "iceberg", "hudi", "delta"} <= formats
    hudi_51 = capability("glue", "5.1", "fta", "hudi", "write", "dataframe")
    delta_51 = capability("glue", "5.1", "fta", "delta", "write", "dataframe")
    fta_60 = capability("glue", "6.0", "fta", "iceberg", "write", "dataframe")
    assert hudi_51["status"] == "version_dependent"
    assert delta_51["status"] == "version_dependent"
    assert fta_60["status"] == "supported"
    assert hudi_51["source"] and hudi_51["limitations"]


def test_review_preflight_is_least_privilege_and_cross_reviewed():
    result = analyze_architecture(
        _payload(
            facts=[
                {
                    "kind": "tf.spark_conf",
                    "subject": {"file": "main.tf", "line": 12},
                    "attrs": {"key": "spark.sql.catalog.source.glue.id", "value": "111111111111"},
                }
            ],
            errors=[
                {
                    "message": "GetDataAccess AccessDeniedException",
                    "source": {"file": "driver.log", "line": 8},
                }
            ],
            evidence={
                "ram": "pending",
                "resource_link": "absent",
                "iam_get_data_access": "denied",
                "lakeformation_permission": "select",
                "registered_location": None,
                "iam_allowed_principals": True,
            },
        )
    )
    review = result["review"]
    preflight = {item["code"]: item for item in review["preflight"]}
    assert preflight["GET-DATA-ACCESS"]["status"] == "fail"
    assert preflight["RAM-SHARE"]["status"] == "fail"
    assert preflight["RESOURCE-LINK"]["status"] == "fail"
    assert preflight["IAMALLOWEDPRINCIPALS"]["status"] == "pass"
    profiles = {item["profile"] for item in review["cross_review"]}
    assert {
        "sf-lake-formation-specialist",
        "sf-security-reviewer",
        "glue-infra-reviewer",
    } <= profiles
    assert "sf-terraform-specialist" in profiles
    assert "pyspark-code-reviewer" in profiles
    serialized = str(review)
    assert "Action: '*'" not in serialized
    assert "Resource: '*'" not in serialized


def test_review_preserves_evidence_and_progressive_disclosure():
    result = analyze_architecture(_payload())
    review = result["review"]
    finops = review["performance_finops"]
    assert finops["observed_measurements"] == []
    assert {"runtime_duration", "workers", "dpu_seconds"} <= set(finops["measurements_required"])
    assert "No numeric gain" in finops["claim_policy"]
    disclosure = review["progressive_disclosure"]
    assert {"glue", "5.1", "fgac", "iceberg", "merge", "cross_account"} <= set(
        disclosure["dimensions"]
    )
    assert "knowledge/storage/iceberg-catalog.md" in disclosure["knowledge_refs"]
    assert not any("emr" in ref for ref in disclosure["knowledge_refs"])


def test_cli_and_mcp_operational_review_parity(tmp_path, capsys):
    payload_path = tmp_path / "architecture.json"
    payload = _payload(
        errors=[
            {
                "message": "GetTemporaryCredentialsForTableV2 AccessDeniedException",
                "source": {"file": "driver.log", "line": 7},
            }
        ]
    )
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["lakeformation", "architect", "--input", str(payload_path)]) == 0
    cli_result = json.loads(capsys.readouterr().out)
    mcp_result = call_tool("sparkforge_lakeformation_architect", {"payload": payload})
    # `_trust` e aditivo de call_tool (FASE 3); formato travado em
    # tests/test_runtime_convergence_trust.py
    mcp_result.pop("_trust", None)
    assert cli_result == mcp_result
    assert "review" in cli_result


def test_operational_closure_docs_and_vnx_are_anchored():
    root = Path(__file__).resolve().parents[1]
    knowledge = (root / "knowledge/lakeformation/operational-closure.md").read_text(
        encoding="utf-8"
    )
    assert "GetTemporaryCredentialsForTableV2" in knowledge
    assert "progressive disclosure" in knowledge
    guide = (root / "docs/guia/usos/lake-formation-operacional.md").read_text(encoding="utf-8")
    assert "MERGE" in guide and "rollback" in guide
    skill = (root / "skills/lakeformation-architecture/SKILL.md").read_text(encoding="utf-8")
    assert "operational review" in skill
    assert "progressive disclosure" in skill
    for path in (
        "agents/sf-lake-formation-specialist.md",
        "agents/sf-terraform-specialist.md",
        "docs/vnext/ARCHITECTURE.md",
        "docs/vnext/CAPABILITY-MATRIX.md",
        "docs/vnext/KNOWLEDGE-MAP.md",
    ):
        text = (root / path).read_text(encoding="utf-8")
        assert "operational" in text.lower() or "runbook" in text.lower()
