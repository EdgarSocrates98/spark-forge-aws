---
sdd: 1
feature: ANALYTICS_ENGINEERING_MICROSCOPE
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/ANALYTICS_ENGINEERING_MICROSCOPE/build_report.md
  sha256: "5fdf25c06e4630e2aea625f966d69cb7f0d9590e5149d895d2036a05d5045218"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, surface_lock, generated_reference, offline_manifest, sources_lock]
deviations:
  - "T1–T3 não registraram red/green porque a implementação precede o build_report; nenhum exit vermelho foi inventado."
  - "A validação direcionada usou basetemp dentro do workspace devido ao WinError 5 no TEMP padrão do host."
---

# ANALYTICS_ENGINEERING_MICROSCOPE — entrega

## Hipótese

Confirmada no escopo offline. Artefatos dbt sustentam lineage e status de
execução sem reexecutar modelos; bundles DuckDB sustentam introspecção
read-only, stats, snapshots e comparações declaradas; lacunas e mutações são
explicitamente unresolved/refused.

## O que foi entregue

- `analyze dbt-artifacts` para manifest, catalog, run_results, models,
  sources, tests, exposures, dependências e materializations.
- `analyze duckdb-microscope` para objetos, colunas, stats, snapshots,
  explain/select observations e equivalências declaradas.
- Tools MCP correspondentes, parity, surface lock, referências, fixtures e
  knowledge operacional.

## Gates rodados

- `python -m pytest tests/test_analytics_microscope.py tests/test_fixtures_golden_analytics.py -q --basetemp .sparkforge_aws/local/pytest-analytics-microscope` — `5 passed`, exit 0.
- `python -m sparkforge_aws.adapters.cli analyze dbt-artifacts --path fixtures/analytics/dbt` — exit 0.
- `python -m sparkforge_aws.adapters.cli analyze duckdb-microscope --path fixtures/analytics/duckdb/microscope.yaml` — exit 0.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .sparkforge_aws/local/pytest-analytics-gates` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge-aws sdd check --repo . --feature ANALYTICS_ENGINEERING_MICROSCOPE` — `ok: true`.

## Limites e rollback

Nenhum dbt, DuckDB, Trino ou Spark é executado durante analyze. O rollback é
reverter os commits da feature em ordem inversa, preservando os artefatos SDD.

## Lições

- dbt manifest é autoridade de lineage; heurística de SQL não deve preencher
  dependência ausente.
- Um microscópio útil pode permanecer offline se o bundle guardar provenance,
  runtime/version e resultado das consultas autorizadas.
