"""Deterministic Lake Formation architecture decision engine."""

from __future__ import annotations

from typing import Any

from sparkforge_aws.lakeformation.capabilities import capability
from sparkforge_aws.lakeformation.catalog_routing import route_catalogs

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
    nodes = list(
        dict.fromkeys(
            ["job", "role"]
            + metadata[1:]
            + data
            + ["target_catalog", "kms"]
            + (
                ["spark", "iceberg", "s3fileio"]
                if "iceberg" in {payload.get("source_format"), payload.get("target_format")}
                else []
            )
        )
    )
    edges = [{"from": left, "to": right} for left, right in zip(nodes, nodes[1:], strict=False)]
    paths = [
        {"name": "metadata", "nodes": metadata},
        {"name": "data", "nodes": data},
    ]
    if "iceberg" in {payload.get("source_format"), payload.get("target_format")}:
        paths.append(
            {
                "name": "iceberg_data",
                "nodes": [
                    "spark",
                    "iceberg",
                    "glue_catalog",
                    "lake_formation",
                    "credential_vending",
                    "s3fileio",
                ],
            }
        )
    return {
        "nodes": nodes,
        "edges": edges,
        "metadata_path": metadata,
        "data_path": data,
        "paths": paths,
        "observability": _observability(payload),
    }


def _observability(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("observability")
    observed = dict(raw) if isinstance(raw, dict) else {}
    cloudtrail_raw = observed.get("cloudtrail")
    cloudtrail = dict(cloudtrail_raw) if isinstance(cloudtrail_raw, dict) else {}
    required: list[str] = []
    legs: dict[str, dict[str, Any]] = {}
    for leg in ("consumer", "producer"):
        value = cloudtrail.get(leg)
        if isinstance(value, dict):
            legs[leg] = dict(value)
            if value.get("status") not in {"present", "observed", "pass", "accepted"}:
                required.append(f"cloudtrail_{leg}")
        elif value in {"present", "observed", "pass", "accepted"}:
            legs[leg] = {"status": value}
        else:
            legs[leg] = {
                "status": "unresolved",
                "required_verification": f"cloudtrail_{leg}",
            }
            if payload.get("cross_account"):
                required.append(f"cloudtrail_{leg}")
    result = {
        "sources": [
            "cloudtrail",
            "glue_logs",
            "spark_logs",
            "lakeformation_audit",
            "ram_state",
        ],
        "cloudtrail": legs,
        "glue_logs": observed.get("glue_logs", "unresolved"),
        "spark_logs": observed.get("spark_logs", "unresolved"),
        "lakeformation_audit": observed.get("lakeformation_audit", "unresolved"),
        "ram_state": observed.get("ram_state", "unresolved"),
        "required_verification": sorted(set(required)),
    }
    result["status"] = "observed" if not required else "unresolved"
    return result


def _authorization(payload: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    operation = str(payload.get("target_operation") or payload.get("operation", "read")).lower()
    return {
        "governance_mode": _governance_mode(payload),
        "table_access_model": str(
            payload.get("table_access_model") or payload.get("access_model", "unknown")
        ).lower(),
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
        "read_operation": operation in _READ_OPERATIONS,
        "write_operation": operation in _WRITE_OPERATIONS,
        "separation": "metadata_authorization != data_authorization",
    }


def _migration_report(payload: dict[str, Any]) -> dict[str, Any]:
    section_names = (
        "runtime_changes",
        "spark_changes",
        "python_changes",
        "iceberg_changes",
        "lakeformation_changes",
        "dynamicframe_implications",
        "fgac_migration",
        "fta_opportunity",
        "cross_account_changes",
        "catalog_routing",
        "ram",
        "catalog_ids",
        "code_changes",
        "terraform_changes",
        "iam_lf_changes",
        "testing_plan",
        "rollback_plan",
    )

    def section(
        items: list[str],
        *,
        status: str | None = None,
        required: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "status": status or ("required" if items else "not_requested"),
            "items": items,
            "required_verification": sorted(set(required or [])),
        }

    def empty_sections() -> dict[str, dict[str, Any]]:
        return {name: section([]) for name in section_names}

    migration = payload.get("migration")
    if not isinstance(migration, dict):
        return {
            "status": "not_requested",
            "from": None,
            "to": None,
            "transition_family": "none",
            "breaking_changes": [],
            "semantic_changes": [],
            "security_changes": [],
            "performance_changes": [],
            "cost_changes": [],
            "testing_plan": [],
            "rollback_plan": ["No migration change is applied by this analyzer."],
            "sections": empty_sections(),
        }
    source_engine = str(migration.get("from_engine") or payload.get("engine") or "")
    target_engine = str(migration.get("to_engine") or payload.get("engine") or "")
    source = str(migration.get("from_runtime", ""))
    target = str(migration.get("to_runtime", ""))
    source_model = str(migration.get("from_access_model") or "").lower()
    target_model = str(migration.get("to_access_model") or "").lower()
    family = "unknown"
    breaking: list[str] = []
    semantic: list[str] = []
    security: list[str] = []
    performance: list[str] = []
    cost: list[str] = []
    if (
        source_model in {"fgac", "fta"}
        and target_model in {"fgac", "fta"}
        and source_model != target_model
    ):
        family = f"{source_model}_to_{target_model}"
        breaking.append(
            f"Access model changes from {source_model.upper()} to {target_model.upper()}."
        )
        semantic.extend(
            [
                "recheck operation permissions",
                "recheck credential path",
                "recheck table format semantics",
            ]
        )
        security.append("revalidate Lake Formation grants, IAM and registered-location behavior")
        performance.append("benchmark the same workload after changing the access model")
        cost.append("compare measured runtime, workers and DPUSeconds only")
    elif source_engine == "glue" and target_engine.startswith("emr"):
        family = "glue_to_emr"
        breaking.append(
            "Glue job semantics do not transfer automatically to the selected EMR deployment mode."
        )
        semantic.extend(
            [
                "recheck Spark and filesystem configuration",
                "recheck catalog and Iceberg integration",
                "recheck job bootstrap and application lifecycle",
            ]
        )
        security.append(
            "revalidate EMR execution role, Lake Formation integration, RAM and credential vending"
        )
        performance.append("benchmark Glue and EMR on the same data volume and operation")
        cost.append("compare measured runtime, workers and platform pricing basis")
    elif source_engine.startswith("emr") and target_engine.startswith("emr") and source != target:
        family = "emr_release_upgrade"
        breaking.append(
            "EMR release changes can alter FGAC/FTA, filesystem and "
            "open-table-format capability cells."
        )
        semantic.extend(
            [
                "recheck release capability matrix",
                "recheck Iceberg/Hudi/Delta operation semantics",
                "recheck EMRFS versus S3A behavior",
            ]
        )
        security.append(
            "revalidate Lake Formation integration, cross-account version and credential path"
        )
        performance.append("repeat the same workload benchmark on the target release")
        cost.append("compare measured DPUSeconds or EMR usage/cost basis only")
    elif source_engine == "glue" and source == "4.0" and target in {"5.0", "5.1"}:
        family = "glue_4_to_5"
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
    elif source_engine == "glue" and source == "5.0" and target == "5.1":
        family = "glue_5.0_to_5.1"
        breaking.append(
            "Revalidate DDL/DML and open-table-format capability cells for the target operation."
        )
        semantic.append("recheck Iceberg/Hudi/Delta operation semantics against the target release")
        security.append("revalidate the target Lake Formation mode and credential path")
        performance.append("repeat the same workload benchmark")
        cost.append("compare measured DPUSeconds only")
    else:
        family = "runtime_transition"
        semantic.append("use the capability matrix for the declared source and target releases")
        cost.append("collect a measured baseline before any capacity or cost claim")
    formats = {
        str(payload.get("source_format") or "").lower(),
        str(payload.get("target_format") or "").lower(),
    }
    source_api = str(payload.get("source_api") or payload.get("api") or "").lower()
    target_api = str(payload.get("target_api") or payload.get("api") or "").lower()
    runtime_items = (
        [f"revalidate {source_engine} {source} → {target_engine} {target}"]
        if source and target
        else []
    )
    spark_items = list(semantic) or [
        "revalidate Spark API and execution semantics for the declared transition"
    ]
    python_items = [
        "verify Python/runtime dependency compatibility on the target engine and release"
    ]
    iceberg_items = (
        [
            "revalidate Iceberg catalog, format version and operation semantics on the target"
        ]
        if "iceberg" in formats or "iceberg" in family
        else []
    )
    lakeformation_items = list(security) or [
        "revalidate Lake Formation access model, grants and credential path"
    ]
    dynamicframe_items = (
        [
            "review DynamicFrame/GlueContext semantics and migrate to the target API "
            "only after bookmarks, pushdown and schema checks"
        ]
        if "dynamicframe" in {source_api, target_api}
        or (source_engine == "glue" and source == "4.0")
        else []
    )
    fgac_items = (
        ["revalidate Spark-native FGAC capability and operation-specific grants"]
        if source_model == "fgac" or target_model == "fgac" or family == "glue_4_to_5"
        else []
    )
    fta_items = (
        [
            "assess FTA only when full-table permission, GetDataAccess and "
            "application integration are verified"
        ]
        if source_model == "fta" or target_model == "fta"
        else []
    )
    cross_account_items = (
        ["revalidate producer/consumer accounts, route and credential path"]
        if payload.get("cross_account")
        else []
    )
    ram_items = (
        ["revalidate RAM share, association, invitation/acceptance and ownership"]
        if payload.get("cross_account")
        else []
    )
    terraform_items = (
        ["review Terraform defaults, Spark configuration and IAM/Lake Formation arguments"]
        if payload.get("terraform")
        or any(
            isinstance(fact, dict) and str(fact.get("kind", "")).startswith("tf.")
            for fact in payload.get("facts", [])
        )
        else []
    )
    sections = {
        "runtime_changes": section(runtime_items),
        "spark_changes": section(spark_items),
        "python_changes": section(python_items),
        "iceberg_changes": section(iceberg_items),
        "lakeformation_changes": section(lakeformation_items),
        "dynamicframe_implications": section(dynamicframe_items),
        "fgac_migration": section(fgac_items),
        "fta_opportunity": section(fta_items),
        "cross_account_changes": section(cross_account_items),
        "catalog_routing": section(
            ["revalidate source/target catalog owner, CatalogId and route"]
        ),
        "ram": section(ram_items),
        "catalog_ids": section(
            ["compare glue.id and glue.account-id independently for source and target"]
        ),
        "code_changes": section(
            ["review source/target API, operation and configuration changes against facts"]
        ),
        "terraform_changes": section(terraform_items),
        "iam_lf_changes": section(
            ["revalidate IAM GetDataAccess, Lake Formation grants, registered location and KMS"]
        ),
        "testing_plan": section(
            [
                "run positive read/write tests for each declared format and operation",
                "run negative tests for catalog routing, credential vending and permissions",
                "compare data correctness before and after; benchmark only with measured runs",
            ]
        ),
        "rollback_plan": section(
            [
                "retain the previous runtime/configuration and catalog route",
                "revert the deployment change after the verification gate fails",
            ]
        ),
    }
    return {
        "status": "required" if breaking else "version_dependent",
        "from": source,
        "to": target,
        "from_engine": source_engine,
        "to_engine": target_engine,
        "transition_family": family,
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
        "sections": sections,
    }


def _preflight(
    payload: dict[str, Any], routing: dict[str, Any], evidence: dict[str, Any]
) -> list[dict[str, Any]]:
    operation = str(payload.get("operation", "read")).lower()
    checks: list[dict[str, Any]] = []

    def add(code: str, layer: str, value: Any, required: str) -> None:
        version_pass = (
            code == "CROSS-ACCOUNT-VERSION"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 4
        )
        status = (
            "pass"
            if value
            in {
                True,
                "allowed",
                "accepted",
                "present",
                "enabled",
                "active",
                "associated",
                "verified",
                "closed",
                "all",
                "super",
            }
            or version_pass
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
        add(
            "RAM-SHARE",
            "ram",
            evidence.get("ram_share_status", evidence.get("ram")),
            "active AWS RAM share",
        )
        add(
            "RAM-ASSOCIATION",
            "ram",
            evidence.get("ram_association"),
            "consumer principal/resource association",
        )
        add(
            "CROSS-ACCOUNT-VERSION",
            "cross_account",
            evidence.get("cross_account_version"),
            "declared Lake Formation cross-account version",
        )
        route = payload.get("cross_account_resolution")
        route_mode = route.get("mode") if isinstance(route, dict) else None
        if route_mode in {None, "resource_link"}:
            add(
                "RESOURCE-LINK",
                "catalog",
                evidence.get("resource_link"),
                "resource link with source name when this route requires one",
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
    dimensions = {
        "security_requirement": {
            "status": "conditional",
            "requires": ["declared_row_column_cell_need", "least_privilege_review"],
        },
        "latency": {
            "status": "conditional",
            "requires": ["same_volume_benchmark", "runtime_duration"],
        },
        "resource_overhead": {
            "status": "conditional",
            "requires": ["workers", "system_user_context_observation"],
        },
        "worker_requirements": {
            "status": "conditional",
            "requires": ["runtime_worker_configuration", "same_volume_benchmark"],
        },
        "runtime_duration": {"status": "conditional", "requires": ["duration_seconds"]},
        "dpu_seconds": {"status": "conditional", "requires": ["dpu_seconds"]},
        "cost": {"status": "conditional", "requires": ["dpu_seconds", "cost_basis"]},
    }
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
        "dimensions": dimensions,
        "claim_policy": "No numeric gain, cost, latency or token saving without measured evidence.",
    }


def _decision_graph(payload: dict[str, Any]) -> dict[str, Any]:
    values = {
        "engine": payload.get("engine"),
        "runtime": payload.get("runtime"),
        "access_model": payload.get("access_model") or payload.get("table_access_model"),
        "format": payload.get("target_format") or payload.get("source_format"),
        "operation": payload.get("target_operation") or payload.get("operation"),
        "cross_account": payload.get("cross_account"),
    }
    nodes = [
        {
            "id": name,
            "value": value,
            "status": "observed" if value not in (None, "") else "unresolved",
        }
        for name, value in values.items()
    ]
    names = list(values)
    edges = [{"from": left, "to": right} for left, right in zip(names, names[1:], strict=False)]
    unresolved = [name for name, value in values.items() if value in (None, "")]
    return {"nodes": nodes, "edges": edges, "dimensions": names, "unresolved": unresolved}


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
    if payload.get("cross_account") and payload.get("engine") == "glue":
        refs.append("knowledge/glue/lakeformation-fgac.md")
    if payload.get("engine") == "emr_ec2":
        refs.append("knowledge/emr/runtime-matrix.md")
    if payload.get("engine") == "emr_serverless":
        refs.append("knowledge/emr-serverless/runtime-matrix.md")
    runbooks = [
        "docs/guia/usos/lake-formation-operacional.md#credential-vending",
        "docs/guia/usos/lake-formation-operacional.md#cross-account",
    ]
    return {
        "dimensions": dimensions,
        "knowledge_refs": list(dict.fromkeys(refs)),
        "runbooks": runbooks,
    }


def _capability_evidence(evidence: dict[str, Any], leg: str) -> Any:
    value = evidence.get(f"{leg}_capability_verification")
    if value is not None:
        return value
    value = evidence.get("capability_verification")
    if isinstance(value, dict):
        return value.get(leg)
    return value


def _capability_decision(
    engine: str,
    runtime: str,
    access_model: str,
    table_format: str,
    operation: str,
    api: str | None,
    leg: str,
    evidence: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], set[str], bool]:
    cell = capability(engine, runtime, access_model, table_format, operation, api)
    status = str(cell.get("status", "unknown"))
    checks: list[dict[str, Any]] = []
    required: set[str] = set()
    hard_block = False
    verification = _capability_evidence(evidence, leg)
    verified = verification in {True, "accepted", "verified", "present", "closed"}
    if status == "unknown":
        required.add("capability_not_declared")
        checks.append(
            _check(
                f"CAPABILITY-{leg.upper()}-UNKNOWN",
                "unresolved",
                "knowledge",
                cell.get("reason", "capability not declared"),
                "capability_not_declared",
            )
        )
    elif status == "not_supported":
        hard_block = True
        checks.append(
            _check(
                "CAPABILITY-NOT-SUPPORTED",
                "blocked",
                "capability",
                (
                    f"{leg} capability is explicitly not_supported for the declared "
                    "release and operation"
                ),
                "choose a supported access model/format/operation or change the runtime",
            )
        )
    elif status == "read_only" and operation in _WRITE_OPERATIONS:
        hard_block = True
        checks.append(
            _check(
                "CAPABILITY-READ-ONLY",
                "blocked",
                "capability",
                f"{leg} capability is read_only but operation is {operation}",
                "use a read operation or choose a capability with write support",
            )
        )
    elif status in {"limited", "version_dependent"} and not verified:
        required.add("capability_specific_verification")
        code = "CAPABILITY-LIMITED" if status == "limited" else "CAPABILITY-VERSION-DEPENDENT"
        checks.append(
            _check(
                code,
                "unresolved",
                "capability",
                f"{leg} capability status {status} needs evidence for the exact operation",
                "capability_specific_verification",
            )
        )
    elif status in {"limited", "version_dependent"}:
        checks.append(
            _check(
                f"CAPABILITY-{status.upper()}",
                "pass",
                "capability",
                f"{leg} capability {status} was closed by declared operation evidence",
                "retain the exact evidence with the deployment record",
            )
        )
    decision = {
        "leg": leg,
        "engine": engine,
        "runtime": runtime,
        "access_model": access_model,
        "format": table_format,
        "operation": operation,
        "api": api,
        "capability": status,
        "status": "blocked" if hard_block else ("unresolved" if required else "consistent"),
        "cell": cell,
        "required_verification": sorted(required),
    }
    return decision, checks, required, hard_block


def _cross_account_resolution(
    payload: dict[str, Any], evidence: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    if not payload.get("cross_account"):
        return {"status": "not_applicable", "mode": "local"}, [], set()
    raw = payload.get("cross_account_resolution")
    resolution = dict(raw) if isinstance(raw, dict) else {}
    mode = str(resolution.get("mode") or "").lower()
    if not mode and evidence.get("resource_link") in {"accepted", "present"}:
        mode = "resource_link"
        resolution["mode"] = mode
    checks: list[dict[str, Any]] = []
    required: set[str] = set()
    if not mode:
        required.update({"cross_account_resolution", "resource_link"})
        checks.append(
            _check(
                "XACC-RESOLUTION",
                "unresolved",
                "cross_account",
                "cross-account access method was not declared",
                (
                    "choose resource_link, explicit_catalog_id, shared_catalog or "
                    "another verified route"
                ),
            )
        )
        return {"status": "unresolved", "mode": None}, checks, required
    if mode == "resource_link":
        value = evidence.get("resource_link")
        if value not in {"accepted", "present", True}:
            required.add("resource_link")
            checks.append(
                _check(
                    "XACC-RESOURCE-LINK",
                    "unresolved",
                    "cross_account",
                    f"resource_link evidence is {value or 'unknown'}",
                    "resource_link",
                )
            )
        return (
            {
                "status": "pass" if not required else "unresolved",
                "mode": mode,
                "service": resolution.get("service"),
            },
            checks,
            required,
        )
    if mode == "explicit_catalog_id":
        catalog_id = resolution.get("catalog_id")
        source_catalog = payload.get("source_catalog")
        source_catalog = source_catalog if isinstance(source_catalog, dict) else {}
        expected = source_catalog.get("glue_id") or source_catalog.get("owner_account_id")
        valid_service = (
            str(payload.get("engine", "")).lower() == "glue"
            and str(resolution.get("service", "glue_etl")).lower() == "glue_etl"
        )
        if not valid_service or not catalog_id or str(catalog_id) != str(expected):
            required.add("cross_account_catalog_id")
            checks.append(
                _check(
                    "XACC-CATALOG-ID",
                    "unresolved",
                    "cross_account",
                    "explicit CatalogId route is not proven for the source catalog",
                    "declare the producer CatalogId for the Glue ETL route",
                )
            )
        return (
            {
                "status": "pass" if not required else "unresolved",
                "mode": mode,
                "catalog_id": catalog_id,
                "service": resolution.get("service", "glue_etl"),
            },
            checks,
            required,
        )
    evidence_key = {
        "shared_catalog": "shared_catalog",
        "other_supported_route": "route_verified",
    }.get(mode)
    if evidence_key is None:
        required.add("cross_account_resolution")
    elif evidence.get(evidence_key) not in {"accepted", "present", "verified", True}:
        required.add(evidence_key)
    if required:
        checks.append(
            _check(
                "XACC-RESOLUTION",
                "unresolved",
                "cross_account",
                f"cross-account route {mode} lacks independent evidence",
                sorted(required),
            )
        )
    return (
        {
            "status": "pass" if not required else "unresolved",
            "mode": mode,
            "service": resolution.get("service"),
        },
        checks,
        required,
    )


def _governance_mode(payload: dict[str, Any]) -> str:
    value = payload.get("access_governance_mode", "lakeformation")
    return str(value).lower()


def _operational_review(
    payload: dict[str, Any],
    routing: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    code_and_iac = _review_code_and_iac(payload)
    taxonomy = _error_taxonomy(payload)
    resolution, _, _ = _cross_account_resolution(payload, evidence)
    return {
        "code_and_iac": code_and_iac,
        "access_explain": _access_explain(payload, evidence),
        "observability": _observability(payload),
        "authorization": _authorization(payload, evidence),
        "error_taxonomy": taxonomy,
        "root_cause": _root_cause(payload, checks + code_and_iac["findings"], taxonomy),
        "migration": _migration_report(payload),
        "preflight": _preflight(payload, routing, evidence),
        "performance_finops": _performance_finops(payload),
        "cross_review": _cross_review(payload, taxonomy),
        "progressive_disclosure": _progressive_disclosure(payload),
        "decision_graph": _decision_graph(payload),
        "cross_account_resolution": resolution,
    }


def analyze_architecture(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze a declared architecture; never calls AWS or invents access."""
    routing = route_catalogs(payload)
    engine = str(payload.get("engine", ""))
    runtime = str(payload.get("runtime", ""))
    access_model = str(
        payload.get("table_access_model") or payload.get("access_model", "unknown")
    ).lower()
    evidence = _evidence(payload)
    error_taxonomy = _error_taxonomy(payload)
    checks: list[dict[str, Any]] = []
    required = set(routing.get("required_verification", []))
    hard_block = bool(error_taxonomy)
    if error_taxonomy:
        for item in error_taxonomy:
            checks.append(
                _check(
                    "OBSERVED-ERROR",
                    "blocked",
                    item["category"],
                    item["message"],
                    item["evidence"],
                )
            )
    observed: list[str] = list(routing.get("observed", []))
    inferred: list[str] = []
    risks: list[str] = []
    rollback: list[str] = [
        (
            "Revert the architecture decision and restore the prior catalog/access "
            "configuration; no AWS mutation is performed."
        )
    ]

    source_format = str(payload.get("source_format") or payload.get("target_format") or "")
    target_format = str(payload.get("target_format") or payload.get("source_format") or "")
    source_operation = str(
        payload.get("source_operation") or payload.get("operation", "read")
    ).lower()
    target_operation = str(
        payload.get("target_operation") or payload.get("operation", "read")
    ).lower()
    source_model = str(payload.get("source_access_model") or access_model).lower()
    target_model = str(payload.get("target_access_model") or access_model).lower()
    source_api = payload.get("source_api") or payload.get("api")
    target_api = payload.get("target_api") or payload.get("api")
    source_decision, source_checks, source_required, source_blocked = _capability_decision(
        engine,
        runtime,
        source_model,
        source_format,
        source_operation,
        source_api,
        "source",
        evidence,
    )
    target_decision, target_checks, target_required, target_blocked = _capability_decision(
        engine,
        runtime,
        target_model,
        target_format,
        target_operation,
        target_api,
        "target",
        evidence,
    )
    checks.extend(source_checks + target_checks)
    required.update(source_required | target_required)
    hard_block = hard_block or source_blocked or target_blocked

    if access_model in {"fgac", "fta"}:
        permission = evidence.get("lakeformation_permission")
        if permission in {False, "denied"}:
            hard_block = True
            checks.append(
                _check(
                    "LF-PERMISSION",
                    "blocked",
                    "lakeformation",
                    "Lake Formation permission was explicitly denied",
                    "grant only the exact operation after resource and principal are proven",
                )
            )
        elif permission in {None, "", "unknown", "absent", "pending"}:
            required.add("lakeformation_permission")
            checks.append(
                _check(
                    "LF-PERMISSION",
                    "unresolved",
                    "lakeformation",
                    "Lake Formation permission was not independently measured",
                    "lakeformation_permission",
                )
            )
    if evidence.get("kms") in {False, "denied"}:
        hard_block = True
        checks.append(
            _check(
                "KMS-DECRYPT",
                "blocked",
                "kms",
                "KMS evidence explicitly denies the governed data path",
                "verify the exact key policy, encryption context and role before changing access",
            )
        )
    for decision in (source_decision, target_decision):
        observed.append(
            f"{decision['leg']} {decision['engine']} {decision['runtime']} "
            f"{decision['access_model']} {decision['format']} "
            f"{decision['operation']}: {decision['capability']}"
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

    migration = payload.get("migration")
    migration_requested = isinstance(migration, dict) or bool(
        payload.get("target_runtime") or payload.get("migration_intent") == "migration"
    )
    migration_required = False
    if (
        migration_requested
        and engine == "glue"
        and runtime == "4.0"
        and access_model == "fgac"
        and (source_api == "dynamicframe" or target_api == "dynamicframe")
    ):
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
        and (source_api == "dynamicframe" or target_api == "dynamicframe")
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

    if payload.get("cross_account") and (source_api == "direct_s3" or target_api == "direct_s3"):
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

    write_operations = {
        value for value in (source_operation, target_operation) if value in _WRITE_OPERATIONS
    }
    if write_operations:
        permission = evidence.get("lakeformation_permission")
        if access_model == "fta" and permission not in {"all", "super"}:
            hard_block = True
            checks.append(
                _check(
                    "LF-WRITE-PERMISSION",
                    "blocked",
                    "lakeformation",
                    (
                        f"write operation {sorted(write_operations)} has {permission or 'unknown'} "
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

    if access_model == "fta" or source_model == "fta" or target_model == "fta":
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

    resolution, resolution_checks, resolution_required = _cross_account_resolution(
        payload, evidence
    )
    checks.extend(resolution_checks)
    required.update(resolution_required)
    if payload.get("cross_account"):
        value = evidence.get("ram")
        if value not in {"accepted", "present", True}:
            required.add("ram")
            checks.append(
                _check(
                    "XACC-RAM",
                    "unresolved",
                    "cross_account",
                    f"cross-account evidence ram={value or 'unknown'} does not prove the share",
                    "ram",
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
        if "cross_account_version" in evidence:
            version = evidence.get("cross_account_version")
            if not isinstance(version, (int, float)) or version < 4:
                required.add("cross_account_version")
                checks.append(
                    _check(
                        "XACC-VERSION",
                        "unresolved",
                        "cross_account",
                        f"cross-account version={version or 'unknown'} is not closed",
                        "cross_account_version",
                    )
                )
    governance_mode = _governance_mode(payload)
    if governance_mode not in {"lakeformation", "iam", "hybrid"}:
        required.add("access_governance_mode")
        checks.append(
            _check(
                "GOVERNANCE-MODE",
                "unresolved",
                "governance",
                f"unknown access_governance_mode={governance_mode}",
                "lakeformation, iam or hybrid",
            )
        )
    if evidence.get("iam_allowed_principals") is True:
        if governance_mode == "hybrid":
            hybrid_requirements = {
                "hybrid_access_enabled": evidence.get("hybrid_access_enabled"),
                "hybrid_principal_opt_in": evidence.get("hybrid_principal_opt_in"),
            }
            if payload.get("cross_account"):
                hybrid_requirements["cross_account_version"] = evidence.get("cross_account_version")
            for key, value in hybrid_requirements.items():
                valid = value is True or value in {"accepted", "present", "enabled", "verified"}
                if key == "cross_account_version":
                    valid = isinstance(value, (int, float)) and value >= 4
                if not valid:
                    required.add(key)
                    checks.append(
                        _check(
                            f"HYBRID-{key.upper()}",
                            "unresolved",
                            "governance",
                            f"hybrid evidence {key}={value or 'unknown'} is not closed",
                            key,
                        )
                    )
        elif governance_mode == "lakeformation":
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
            "table_access_model": access_model,
            "access_governance_mode": governance_mode,
            "capability": target_decision["capability"],
            "source_decision": source_decision,
            "target_decision": target_decision,
            "capability_checks": [item for item in checks if item.get("layer") == "capability"],
            "observed": observed,
            "inferred": inferred,
            "required_verification": sorted(required),
            "risks": risks,
            "rollback": rollback,
            "cross_account_resolution": resolution,
        },
        "review": _operational_review(payload, routing, checks, evidence),
    }


__all__ = ["analyze_architecture"]
