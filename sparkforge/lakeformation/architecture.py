"""Deterministic Lake Formation architecture decision engine."""

from __future__ import annotations

from typing import Any

from sparkforge.lakeformation.capabilities import capability
from sparkforge.lakeformation.catalog_routing import route_catalogs

_READ_OPERATIONS = {"read", "select", "describe"}
_WRITE_OPERATIONS = {"write", "insert", "update", "delete", "merge", "ddl"}
_LF_CONFIG_PREFIXES = (
    "spark.sql.catalog.",
    "spark.hadoop.fs.s3.",
    "spark.hadoop.fs.s3a.",
)
_ACCESS_KINDS = {"pyspark.read", "pyspark.write", "pyspark.sql", "pyspark.action"}


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


def _fact_anchor(fact: dict[str, Any]) -> str:
    subject = fact.get("subject") if isinstance(fact.get("subject"), dict) else {}
    file = subject.get("file") or fact.get("file") or "<unknown>"
    line = subject.get("line") or fact.get("line")
    return f"{file}:{line}" if line is not None else str(file)


def _fact_line(fact: dict[str, Any]) -> int | None:
    subject = fact.get("subject") if isinstance(fact.get("subject"), dict) else {}
    value = subject.get("line", fact.get("line"))
    return value if isinstance(value, int) else None


def _fact_file(fact: dict[str, Any]) -> str:
    subject = fact.get("subject") if isinstance(fact.get("subject"), dict) else {}
    return str(subject.get("file") or fact.get("file") or "<unknown>")


def _fact_attrs(fact: dict[str, Any]) -> dict[str, Any]:
    value = fact.get("attrs")
    return dict(value) if isinstance(value, dict) else {}


def _review_code_and_iac(payload: dict[str, Any]) -> dict[str, Any]:
    facts = [fact for fact in payload.get("facts", []) if isinstance(fact, dict)]
    engine = str(payload.get("engine", ""))
    runtime = str(payload.get("runtime", ""))
    access_model = str(payload.get("access_model", "unknown")).lower()
    findings: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    required: set[str] = set()

    for fact in facts:
        kind = str(fact.get("kind", ""))
        if kind.startswith(("pyspark.", "tf.", "spark.conf")):
            observed.append(
                {"kind": kind, "source": _fact_anchor(fact), "attrs": _fact_attrs(fact)}
            )

    accesses = [fact for fact in facts if str(fact.get("kind", "")) in _ACCESS_KINDS]
    first_access: dict[str, int] = {}
    for fact in accesses:
        line = _fact_line(fact)
        if line is not None:
            file = _fact_file(fact)
            first_access[file] = min(line, first_access.get(file, line))

    for fact in facts:
        kind = str(fact.get("kind", ""))
        attrs = _fact_attrs(fact)
        api = str(attrs.get("api") or attrs.get("implementation") or "").lower()
        if (
            engine == "glue"
            and runtime in {"5.0", "5.1", "6.0"}
            and access_model == "fgac"
            and (
                kind == "pyspark.glue_context_init"
                and "dynamicframe" in api
                or kind in {"pyspark.read", "pyspark.write"}
                and api == "dynamicframe"
            )
        ):
            findings.append(
                {
                    "code": "DYNAMICFRAME-FGAC",
                    "status": "blocked",
                    "layer": "api",
                    "evidence": [_fact_anchor(fact)],
                    "required_verification": (
                        "migrate to Spark DataFrame/Spark SQL and recheck semantics"
                    ),
                }
            )
        target = str(attrs.get("target") or attrs.get("path") or "")
        if access_model in {"fgac", "fta"} and target.startswith("s3://"):
            findings.append(
                {
                    "code": "DIRECT-S3-GOVERNED",
                    "status": "blocked",
                    "layer": "catalog",
                    "evidence": [_fact_anchor(fact)],
                    "required_verification": (
                        "declare the Glue Catalog/Lake Formation route before replacing "
                        "a governed table"
                    ),
                }
            )
        key = str(attrs.get("key") or "")
        if kind in {"pyspark.conf_set", "tf.spark_conf", "spark.conf_effective"} and (
            key.startswith(_LF_CONFIG_PREFIXES) or "lakeformation" in key.lower()
        ):
            line = _fact_line(fact)
            file = _fact_file(fact)
            if kind in {"pyspark.conf_set", "spark.conf_effective"} and (
                line is None or file not in first_access or line > first_access[file]
            ):
                findings.append(
                    {
                        "code": "LATE-LF-CONFIG",
                        "status": "blocked",
                        "layer": "spark_session",
                        "evidence": [_fact_anchor(fact)],
                        "required_verification": "spark_session_before_lf_config",
                    }
                )
                required.add("spark_session_before_lf_config")

    if (
        access_model == "fgac"
        and accesses
        and not any(
            str(fact.get("kind", "")) in {"pyspark.conf_set", "tf.spark_conf"}
            and "lakeformation" in str(_fact_attrs(fact).get("key", "")).lower()
            for fact in facts
        )
    ):
        required.add("spark_session_before_lf_config")

    status = (
        "blocked"
        if any(item["status"] == "blocked" for item in findings)
        else ("unresolved" if required else "consistent")
    )
    return {
        "status": status,
        "observed": observed,
        "findings": findings,
        "required_verification": sorted(required),
    }


_ERROR_PATTERNS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "credential_vending",
        ("getdataaccess", "gettemporarycredentialsfortable", "credential vending"),
        ("iam", "lakeformation", "catalog", "registered_location", "storage"),
    ),
    (
        "catalog_routing",
        (
            "entitynotfound",
            "nosuchtable",
            "nosuchnamespace",
            "database not found",
            "table not found",
        ),
        ("catalog_id", "glue.id", "account", "region", "resource_link"),
    ),
    (
        "lakeformation",
        ("insufficient lake formation", "lake formation permission", "lakeformation accessdenied"),
        ("select", "describe", "insert", "delete", "alter", "all"),
    ),
    (
        "ram",
        ("resource share", "ram", "shared table invisible", "resource unavailable"),
        ("share", "association", "invitation", "ownership"),
    ),
    (
        "kms",
        ("kms", "decrypt", "generatedatakey", "encryption context"),
        ("key_policy", "kms:decrypt", "encryption_context"),
    ),
    (
        "s3",
        ("403", "s3 accessdenied", "s3 access denied"),
        ("credential_path", "bucket_policy", "storage"),
    ),
)


def _error_taxonomy(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in payload.get("errors", []):
        if not isinstance(item, dict):
            continue
        message = str(item.get("message", ""))
        lowered = message.lower()
        match = next(
            (
                pattern
                for pattern in _ERROR_PATTERNS
                if any(token in lowered for token in pattern[1])
            ),
            None,
        )
        if match is None:
            category, checks = "unknown", ["capture the original error and runtime context"]
        else:
            category, checks = match[0], list(match[2])
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        anchor = (
            f"{source.get('file', '<unknown>')}:{source.get('line')}"
            if source.get("line") is not None
            else str(source.get("file", "<unknown>"))
        )
        output.append(
            {
                "category": category,
                "message": message,
                "evidence": [anchor],
                "possible_layers": checks,
                "checks": checks,
            }
        )
    return output


def _root_cause(
    payload: dict[str, Any], checks: list[dict[str, Any]], taxonomy: list[dict[str, Any]]
) -> dict[str, Any]:
    blocked = [check for check in checks if check.get("status") == "blocked"]
    if not taxonomy and not blocked:
        return {
            "status": "unresolved",
            "symptom": "no_error_or_blocking_evidence",
            "possible_layers": [],
            "evidence": [],
            "hypotheses": [],
            "checks": ["collect the original error, runtime and authorization facts"],
            "required_proof": ["error_signature", "runtime", "authorization_facts"],
            "fix": [],
            "verification": ["re-run the same operation after evidence is collected"],
        }
    categories = [item["category"] for item in taxonomy]
    layers = sorted({layer for item in taxonomy for layer in item["possible_layers"]})
    evidence = [anchor for item in taxonomy for anchor in item["evidence"]]
    required: list[str] = []
    if "credential_vending" in categories:
        required.extend(
            [
                "lakeformation:GetDataAccess",
                "lakeformation_permission",
                "registered_location",
                "catalog_ownership",
            ]
        )
    if "catalog_routing" in categories:
        required.extend(["CatalogId", "glue.id", "glue.account-id", "resource_link"])
    if "ram" in categories:
        required.extend(["ram_share", "ram_association", "cross_account_version"])
    if "kms" in categories:
        required.extend(["kms:Decrypt", "key_policy", "encryption_context"])
    if "s3" in categories:
        required.extend(["credential_path", "bucket_policy", "registered_location"])
    for check in blocked:
        required.extend(check.get("required_verification", []))
    return {
        "status": "blocked" if blocked or taxonomy else "unresolved",
        "symptom": taxonomy[0]["message"] if taxonomy else "blocking architecture check",
        "possible_layers": sorted(
            set(categories + layers) if taxonomy else {check.get("layer") for check in blocked}
        ),
        "evidence": evidence + [item.get("evidence") for item in blocked],
        "hypotheses": [
            f"{category} layer requires independent evidence" for category in categories
        ],
        "checks": [item["checks"] for item in taxonomy] + [item.get("code") for item in blocked],
        "required_proof": sorted(set(required)),
        "fix": [
            (
                "Grant only the exact action/resource required after the named layer "
                "is proven; do not add wildcard permissions."
            ),
            (
                "Preserve the governed catalog and credential path until the failing "
                "layer is verified."
            ),
        ],
        "verification": ["repeat the failed operation and compare the new evidence anchors"],
    }


def _access_explain(payload: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    metadata = ["job", "glue_catalog", "lake_formation"]
    data = ["lake_formation"]
    if payload.get("cross_account"):
        data.extend(["ram", "producer_catalog"])
    if evidence.get("registered_location") is not False:
        data.append("credential_vending")
    data.append("s3")
    nodes = list(dict.fromkeys(metadata + data + ["target_catalog", "kms"]))
    edges = [
        {"from": left, "to": right}
        for left, right in zip(nodes, nodes[1:], strict=False)
    ]
    return {"nodes": nodes, "edges": edges, "metadata_path": metadata, "data_path": data}


def _authorization(payload: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "metadata": {
            "catalog": evidence.get("catalog_metadata", "unknown"),
            "lakeformation": evidence.get("lakeformation_permission", "unknown"),
        },
        "data": {
            "registered_location": evidence.get("registered_location", "unknown"),
            "credential_vending": evidence.get("iam_get_data_access", "unknown"),
            "storage": evidence.get("storage", "unknown"),
            "kms": evidence.get("kms", "unknown"),
        },
        "read_operation": str(payload.get("operation", "read")).lower() in _READ_OPERATIONS,
        "write_operation": str(payload.get("operation", "read")).lower() in _WRITE_OPERATIONS,
        "separation": "metadata_authorization != data_authorization",
    }


def _migration_report(payload: dict[str, Any]) -> dict[str, Any]:
    migration = payload.get("migration")
    if not isinstance(migration, dict):
        return {
            "status": "not_requested",
            "from": None,
            "to": None,
            "breaking_changes": [],
            "semantic_changes": [],
            "security_changes": [],
            "performance_changes": [],
            "cost_changes": [],
            "testing_plan": [],
            "rollback_plan": ["No migration change is applied by this analyzer."],
        }
    source = str(migration.get("from_runtime", ""))
    target = str(migration.get("to_runtime", ""))
    breaking: list[str] = []
    semantic: list[str] = []
    security: list[str] = []
    performance: list[str] = []
    cost: list[str] = []
    if source == "4.0" and target in {"5.0", "5.1"}:
        breaking.append(
            "FGAC moves from GlueContext/DynamicFrame semantics to the Spark-native path."
        )
        semantic.extend(
            [
                "recheck bookmarks",
                "pushdown predicates",
                "schema handling",
                "Iceberg catalog configuration",
            ]
        )
        security.append("revalidate FGAC/FTA mode, resource links, grants and GetDataAccess")
        performance.append("measure system/user context overhead against a same-volume baseline")
        cost.append("measure runtime duration, workers and DPUSeconds; no saving is inferred")
    elif source == "5.0" and target == "5.1":
        breaking.append(
            "Revalidate DDL/DML and open-table-format capability cells for the target operation."
        )
        semantic.append("recheck Iceberg/Hudi/Delta operation semantics against the target release")
        security.append("revalidate the target Lake Formation mode and credential path")
        performance.append("repeat the same workload benchmark")
        cost.append("compare measured DPUSeconds only")
    else:
        semantic.append("use the capability matrix for the declared source and target releases")
        cost.append("collect a measured baseline before any capacity or cost claim")
    return {
        "status": "required" if breaking else "version_dependent",
        "from": source,
        "to": target,
        "breaking_changes": breaking,
        "semantic_changes": semantic,
        "security_changes": security,
        "performance_changes": performance,
        "cost_changes": cost,
        "testing_plan": [
            "run positive read/write tests for each declared format and operation",
            "run negative tests for catalog routing, credential vending and permissions",
            "compare data correctness before and after; benchmark only with measured runs",
        ],
        "rollback_plan": [
            "retain the previous runtime/configuration and catalog route",
            "revert the deployment change after the verification gate fails",
        ],
    }


def _preflight(
    payload: dict[str, Any], routing: dict[str, Any], evidence: dict[str, Any]
) -> list[dict[str, Any]]:
    operation = str(payload.get("operation", "read")).lower()
    checks: list[dict[str, Any]] = []

    def add(code: str, layer: str, value: Any, required: str) -> None:
        status = (
            "pass"
            if value in {True, "allowed", "accepted", "present", "enabled", "all", "super"}
            else ("fail" if value in {False, "denied", "absent", "pending"} else "unresolved")
        )
        checks.append(
            {
                "code": code,
                "layer": layer,
                "status": status,
                "evidence": value,
                "required_verification": required,
            }
        )

    add(
        "CATALOG-OWNERSHIP", "catalog", routing.get("status") == "ok", "catalog owner and CatalogId"
    )
    add(
        "LF-PERMISSION",
        "lakeformation",
        evidence.get("lakeformation_permission"),
        "permission for the declared operation",
    )
    add(
        "REGISTERED-LOCATION",
        "lakeformation",
        evidence.get("registered_location"),
        "registered_location",
    )
    if payload.get("cross_account"):
        add("RAM-SHARE", "ram", evidence.get("ram"), "active share and association")
        add(
            "RESOURCE-LINK",
            "catalog",
            evidence.get("resource_link"),
            "resource link with source name",
        )
    if payload.get("cross_account") or str(payload.get("access_model", "")).lower() == "fta":
        add(
            "GET-DATA-ACCESS",
            "credential_vending",
            evidence.get("iam_get_data_access"),
            "lakeformation:GetDataAccess",
        )
    add("KMS", "encryption", evidence.get("kms"), "KMS key policy and encryption context")
    add(
        "IAMALLOWEDPRINCIPALS",
        "governance",
        evidence.get("iam_allowed_principals"),
        "hybrid opt-in or explicit governance decision",
    )
    add(
        "OPERATION",
        "authorization",
        operation,
        f"permissions for {operation}, not SELECT by analogy",
    )
    return checks


def _performance_finops(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = payload.get("benchmark") if isinstance(payload.get("benchmark"), dict) else {}
    observed = []
    for key in ("duration_seconds", "workers", "dpu_seconds", "cost_basis"):
        if key in evidence:
            observed.append(
                {"metric": key, "value": evidence[key], "source": "declared benchmark/run fact"}
            )
    return {
        "claims": [
            {
                "model": "FGAC",
                "impact": "system/user context enforcement may affect latency and worker needs",
                "status": "conditional",
                "requires": ["same_volume_benchmark", "runtime_duration", "workers"],
            },
            {
                "model": "FTA",
                "impact": "full-table access avoids fine-grained filtering when policy permits",
                "status": "conditional",
                "requires": ["same_volume_benchmark", "dpu_seconds"],
            },
        ],
        "measurements_required": [
            "runtime_duration",
            "workers",
            "dpu_seconds",
            "same_volume_correctness_check",
        ],
        "observed_measurements": observed,
        "claim_policy": "No numeric gain, cost, latency or token saving without measured evidence.",
    }


def _cross_review(payload: dict[str, Any], taxonomy: list[dict[str, Any]]) -> list[dict[str, str]]:
    selected: list[str] = ["sf-lake-formation-specialist"]
    if payload.get("cross_account"):
        selected.append("sf-security-reviewer")
    if payload.get("engine") == "glue":
        selected.append("glue-infra-reviewer")
    if payload.get("target_format") == "iceberg" or payload.get("source_format") == "iceberg":
        selected.append("iceberg-performance-engineer")
    if any(
        str(fact.get("kind", "")).startswith("tf.")
        for fact in payload.get("facts", [])
        if isinstance(fact, dict)
    ):
        selected.append("sf-terraform-specialist")
    if any(item.get("category") == "credential_vending" for item in taxonomy):
        selected.append("pyspark-code-reviewer")
    return [
        {"profile": name, "reason": "review only; no subagent or AWS mutation is implied"}
        for name in dict.fromkeys(selected)
    ]


def _progressive_disclosure(payload: dict[str, Any]) -> dict[str, Any]:
    dimensions = [
        value
        for value in (
            payload.get("engine"),
            payload.get("runtime"),
            payload.get("access_model"),
            payload.get("source_format") or payload.get("target_format"),
            payload.get("operation"),
            "cross_account" if payload.get("cross_account") else None,
        )
        if value
    ]
    refs = [
        "knowledge/lakeformation/capability-matrix.yaml",
        "knowledge/lakeformation/operational-closure.md",
    ]
    formats = {payload.get("source_format"), payload.get("target_format")}
    if "iceberg" in formats:
        refs.append("knowledge/storage/iceberg-catalog.md")
    if payload.get("engine") == "glue":
        refs.append("knowledge/glue/lakeformation-fgac.md")
    if payload.get("cross_account"):
        refs.append("knowledge/glue/lakeformation-fgac.md")
    runbooks = [
        "docs/guia/usos/lake-formation-operacional.md#credential-vending",
        "docs/guia/usos/lake-formation-operacional.md#cross-account",
    ]
    return {
        "dimensions": dimensions,
        "knowledge_refs": list(dict.fromkeys(refs)),
        "runbooks": runbooks,
    }


def _operational_review(
    payload: dict[str, Any],
    routing: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    code_and_iac = _review_code_and_iac(payload)
    taxonomy = _error_taxonomy(payload)
    return {
        "code_and_iac": code_and_iac,
        "access_explain": _access_explain(payload, evidence),
        "authorization": _authorization(payload, evidence),
        "error_taxonomy": taxonomy,
        "root_cause": _root_cause(payload, checks + code_and_iac["findings"], taxonomy),
        "migration": _migration_report(payload),
        "preflight": _preflight(payload, routing, evidence),
        "performance_finops": _performance_finops(payload),
        "cross_review": _cross_review(payload, taxonomy),
        "progressive_disclosure": _progressive_disclosure(payload),
    }


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
            "A blind DynamicFrame-to-direct-S3 replacement can bypass the governed catalog path."
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
        "review": _operational_review(payload, routing, checks, evidence),
    }


__all__ = ["analyze_architecture"]
