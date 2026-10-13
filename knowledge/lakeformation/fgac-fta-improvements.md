# FGAC/FTA decision improvements

## Contrato de decisão

`analyze_architecture` permanece offline. A entrada declara engine, runtime,
`table_access_model`/`access_model`, source/target format and operation, catalog
ownership, evidence and optional migration intent. O output preserva
`decision.capability` for compatibility and adds `source_decision` and
`target_decision`.

Each leg is evaluated independently:

- `not_supported` is `blocked`;
- `read_only` is `blocked` for write operations and can pass for reads;
- `limited` and `version_dependent` require exact capability evidence;
- `unknown` remains `unresolved` and names the source needed to close it.

The status of a capability is not inferred from a neighboring release, access
model, format or operation. A supplied `capability_verification` closes only a
declared `limited` or `version_dependent` cell; it cannot promote
`not_supported`.

## Source and target

Use `source_operation` and `target_operation` when a job reads one governed
table and writes another. For example, Parquet `read` in producer account and
Iceberg `merge` in consumer account produce two cells, two capability checks and
one combined status. `operation` remains fallback for legacy payloads.

## Cross-account resolution

`cross_account_resolution.mode` makes catalog routing explicit:

- `resource_link` requires resource-link evidence;
- `explicit_catalog_id` is valid for the Glue ETL route when `catalog_id` equals
  the source catalog id; it does not require a resource link;
- `shared_catalog` and `other_supported_route` require their own evidence;
- absent mode is unresolved, not an automatic resource-link failure.

RAM/share, catalog ownership and credential vending remain independent checks.
Direct S3 never replaces the governed catalog route.

## Governance versus table access

`table_access_model` (`fgac` or `fta`) answers how the table is accessed.
`access_governance_mode` (`lakeformation`, `iam` or `hybrid`) answers how
governance is administered. In `hybrid`, `IAMAllowedPrincipals` is not a
blanket blocker: the analyzer requires Hybrid Access registration, principal
opt-in and, for cross-account, cross-account version 4 or higher. In ordinary
Lake Formation mode, the compatibility grant remains a blocking conflict.

This distinction follows the AWS Hybrid Access procedure: existing principals
are opted in before enabling the location, while IAM permissions can continue
for non-opted-in principals.

## Glue 4.0 and migration

Glue 4.0 FGAC with DynamicFrame/GlueContext is a current architecture cell. It
becomes `migration_required` only when `migration`, `target_runtime` or an
explicit migration intent is declared. The analyzer does not classify every
legacy job as broken merely because Glue 5.x has a different Spark-native path.

## Catalog IDs

Routing keeps `glue.id` and `glue.account-id` independent. It compares:

- `glue.id` to catalog owner;
- `glue.account-id` to `expected_glue_account_id` when the integration declares
  that context.

A difference between the two properties is not itself an invalid architecture.
Without the expected context, the result is unresolved and asks for the missing
semantic evidence.

## Fontes

- AWS Lake Formation resource links and Glue ETL CatalogId route:
  https://docs.aws.amazon.com/lake-formation/latest/dg/resource-links-about.html
- AWS Lake Formation cross-account prerequisites:
  https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-prereqs.html
- AWS Lake Formation Hybrid Access mode:
  https://docs.aws.amazon.com/lake-formation/latest/dg/hybrid-access-mode-update.html
- AWS Glue fine-grained access control:
  https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable.html
- AWS Glue 5.1 migration:
  https://docs.aws.amazon.com/glue/latest/dg/migrating-version-51.html
- AWS Glue 6.0 migration:
  https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html
