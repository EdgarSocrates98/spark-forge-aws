---
sdd: 1
feature: ANALYTICS_ENGINEERING_MICROSCOPE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/ANALYTICS_ENGINEERING_MICROSCOPE/design.md
  sha256: "e0904abd013be82136ce307c35a26156704e4549c738563e27fa95f35bc14c61"
tasks:
  - id: T1
    files: [sparkforge_aws/analytics/__init__.py, sparkforge_aws/analytics/dbt.py, fixtures/analytics/dbt/manifest.json, fixtures/analytics/dbt/catalog.json, fixtures/analytics/dbt/run_results.json, tests/test_analytics_microscope.py]
    covers: [AC1]
    test: {path: tests/test_analytics_microscope.py, name: test_dbt_artifacts_preserve_lineage_and_results}
  - id: T2
    files: [sparkforge_aws/analytics/duckdb.py, fixtures/analytics/duckdb/microscope.yaml, tests/test_analytics_microscope.py]
    covers: [AC2]
    test: {path: tests/test_analytics_microscope.py, name: test_duckdb_microscope_is_read_only_and_structured}
  - id: T3
    files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, parity.yaml, docs/knowledge/analytics-engineering-microscope.md]
    covers: [AC3]
    test: {path: tests/test_analytics_microscope.py, name: test_analytics_surfaces_share_contracts}
---

# ANALYTICS_ENGINEERING_MICROSCOPE — plano

## T1 — dbt artifacts

Implementar parser offline de manifest/catalog/run_results e dependências.

Commit: `feat(analytics): analyze dbt artifacts and lineage`

## T2 — DuckDB microscope

Implementar bundle read-only com introspecção de objetos, stats e SQL
equivalence declarada.

Commit: `feat(analytics): add duckdb microscope contract`

## T3 — superfícies

Registrar CLI/MCP, parity e documentação.

Commit: `feat(analytics): expose analytics microscope analyzers`
