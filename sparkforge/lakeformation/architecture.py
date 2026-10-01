"""Deterministic Lake Formation architecture decision engine."""

from __future__ import annotations

from typing import Any

from sparkforge.lakeformation.capabilities import capability
from sparkforge.lakeformation.catalog_routing import route_catalogs

_READ_OPERATIONS = {"read", "select", "describe"}
_WRITE_OPERATIONS = {"write", "insert", "update", "delete", "merge", "ddl"}


def _check(
    code: str,
    status: str,
    layer: str,
    evidence: str,
    required_verification: str | list[str] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "code": code,
        "status": status,
        "layer": layer,
        "evidence": evidence,
    }
    if required_verification:
        item["required_verification"] = required_verification
    return item


def _evidence(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("evidence")
    return dict(value) if isinstance(value, dict) else {}


def analyze_architecture(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze a declared architecture; never calls AWS or invents access."""
    routing = route_catalogs(payload)
    engine = str(payload.get("engine", ""))
    runtime = str(payload.get("runtime", ""))
    access_model = str(payload.get("access_model", "unknown")).lower()
    table_format = str(payload.get("target_format") or payload.get("source_format") or "")
    operation = str(payload.get("operation", "read")).lower()
    api = payload.get("api")
    evidence = _evidence(payload)
    checks: list[dict[str, Any]] = []
    required = set(routing.get("required_verification", []))
    hard_block = False
    migration_required = False
    observed: list[str] = list(routing.get("observed", []))
    inferred: list[str] = []
    risks: list[str] = []
    rollback: list[str] = [
        (
            "Revert the architecture decision and restore the prior catalog/access "
            "configuration; no AWS mutation is performed."
        )
    ]

    cell = capability(engine, runtime, access_model, table_format, operation, api)
    if cell.get("status") == "unknown":
        required.add("capability_not_declared")
        checks.append(
            _check(
                "CAPABILITY-UNKNOWN",
                "unresolved",
                "knowledge",
                cell.get("reason", "capability not declared"),
                "capability_not_declared",
            )
        )
    else:
        observed.append(
            f"{engine} {runtime} {access_model} {table_format} {operation}: {cell['status']}"
        )

    if access_model == "both":
        hard_block = True
        checks.append(
            _check(
                "LF-MODE-CONFLICT",
                "blocked",
                "access_model",
                "FGAC and FTA cannot be enabled on the same job or EMR application.",
                "select exactly one access_model",
            )
        )

    if engine == "glue" and runtime == "4.0" and access_model == "fgac" and api == "dynamicframe":
        migration_required = True
        checks.append(
            _check(
                "GLUE-LF-MIGRATION",
                "blocked",
                "runtime",
                (
                    "Glue 4.0 DynamicFrame/GlueContext is a different Lake Formation "
                    "access architecture from Glue 5.x Spark-native FGAC."
                ),
                "migrate the API and verify bookmarks, pushdown and schema semantics",
            )
        )
        risks.append(
            "A blind DynamicFrame-to-direct-S3 replacement can bypass the governed "
            "catalog path."
        )

    if (
        engine == "glue"
        and runtime in {"5.0", "5.1"}
        and access_model == "fgac"
        and api == "dynamicframe"
    ):
        hard_block = True
        checks.append(
            _check(
                "GLUE-LF-DYNAMICFRAME",
                "blocked",
                "api",
                (
                    "Glue 5.x FGAC is Spark-native; the old DynamicFrame path is not "
                    "the verified FGAC path."
                ),
                "use Spark DataFrame/Spark SQL after a semantic migration review",
            )
        )

    if payload.get("cross_account") and api == "direct_s3":
        hard_block = True
        checks.append(
            _check(
                "PARQUET-GOVERNANCE",
                "blocked",
                "catalog",
                (
                    "A governed table must retain its Glue Catalog/Lake Formation "
                    "route; direct S3 is not a generic cross-account fix."
                ),
                "declare the governed catalog and resource-link route",
            )
        )

    if operation in _WRITE_OPERATIONS:
        permission = evidence.get("lakeformation_permission")
        if access_model == "fta" and permission not in {"all", "super"}:
            hard_block = True
            checks.append(
                _check(
                    "LF-WRITE-PERMISSION",
                    "blocked",
                    "lakeformation",
                    (
                        f"write operation {operation} has {permission or 'unknown'} "
                        "rather than full-table permission"
                    ),
                    "ALL or SUPER",
                )
            )
        if access_model == "fgac" and evidence.get("registered_location") is True:
            risks.append(
                "FGAC write on a registered location requires a release-specific "
                "authorization check; do not infer from SELECT."
            )

    if access_model == "fta":
        get_data_access = evidence.get("iam_get_data_access")
        if get_data_access == "denied":
            hard_block = True
            checks.append(
                _check(
                    "IAM-GETDATAACCESS",
                    "blocked",
                    "credential_vending",
                    "runtime role cannot request Lake Formation-vended credentials",
                    "lakeformation:GetDataAccess",
                )
            )
        elif get_data_access != "allowed":
            required.add("iam_get_data_access")
            checks.append(
                _check(
                    "IAM-GETDATAACCESS",
                    "unresolved",
                    "credential_vending",
                    "GetDataAccess was not measured",
                    "iam_get_data_access",
                )
            )
        if evidence.get("application_integration") != "enabled":
            required.add("application_integration")
            checks.append(
                _check(
                    "LF-APPLICATION-INTEGRATION",
                    "unresolved",
                    "credential_vending",
                    "FTA application integration was not proven enabled",
                    "application_integration",
                )
            )
        if engine == "glue" and runtime == "5.1" and evidence.get("filesystem") != "emrfs":
            required.add("filesystem_emrfs")
            checks.append(
                _check(
                    "FTA-FILESYSTEM",
                    "unresolved",
                    "filesystem",
                    "Glue 5.1 FTA requires an explicitly verified compatible filesystem path",
                    "filesystem_emrfs",
                )
            )

    if payload.get("cross_account"):
        for key in ("ram", "resource_link"):
            value = evidence.get(key)
            if value != "accepted" and value != "present":
                required.add(key)
                checks.append(
                    _check(
                        f"XACC-{key.upper()}",
                        "unresolved",
                        "cross_account",
                        (
                            f"cross-account evidence {key}={value or 'unknown'} does "
                            "not prove the route"
                        ),
                        key,
                    )
                )
        if access_model != "fta" and evidence.get("iam_get_data_access") != "allowed":
            required.add("iam_get_data_access")
            checks.append(
                _check(
                    "XACC-IAM-GETDATAACCESS",
                    "unresolved",
                    "cross_account",
                    "cross-account credential-vending evidence was not measured",
                    "iam_get_data_access",
                )
            )
        if evidence.get("iam_allowed_principals") is True:
            hard_block = True
            checks.append(
                _check(
                    "LF-IAMALLOWEDPRINCIPALS",
                    "blocked",
                    "governance",
                    "IAMAllowedPrincipals keeps IAM compatibility access on the governed resource",
                    "revoke compatibility grants only with governance owner approval",
                )
            )

    if migration_required:
        decision_model = "migration_required"
    elif access_model in {"fgac", "fta"}:
        decision_model = access_model.upper()
    else:
        decision_model = "unresolved"
        required.add("access_model")

    if required and not hard_block:
        status = "unresolved"
    elif hard_block:
        status = "blocked"
    else:
        status = "consistent"

    return {
        "status": status,
        "routing": routing,
        "checks": checks,
        "decision": {
            "access_model": decision_model,
            "capability": cell.get("status", "unknown"),
            "observed": observed,
            "inferred": inferred,
            "required_verification": sorted(required),
            "risks": risks,
            "rollback": rollback,
        },
    }


__all__ = ["analyze_architecture"]
