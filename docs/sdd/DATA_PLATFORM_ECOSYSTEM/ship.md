---
sdd: 1
feature: DATA_PLATFORM_ECOSYSTEM
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/DATA_PLATFORM_ECOSYSTEM/build_report.md
  sha256: "67bb8417a41cb1e10aac96acb782b18b6d0f3aa3cdb3737ea8e635c93c5720ed"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, surface_lock, generated_reference, offline_manifest, sources_lock]
deviations:
  - "T1–T3 não registraram red/green porque a implementação precede o build_report; nenhum exit vermelho foi inventado."
  - "A validação direcionada usou basetemp dentro do workspace devido ao WinError 5 no TEMP padrão do host."
---

# DATA_PLATFORM_ECOSYSTEM — entrega

## Hipótese

Confirmada no escopo offline. Serving/OLAP, ingestion/CDC, AI Data Engineering
e radar compartilham categorias, ownership, bindings, evidence e reliability
controls; controles ausentes ficam unresolved e radar não vira dependência de
runtime.

## O que foi entregue

- Inventário de Trino, Redshift, ClickHouse, Pinot, Druid, DuckDB, Snowflake,
  BigQuery, Airbyte, Meltano, Kafka Connect, Debezium, DMS, JDBC, APIs, SFTP,
  SaaS, mainframe, SAP, Feast, feature stores, vector indexes e modelos.
- Connector Reliability Model com idempotência, checkpointing, retry, DLQ,
  rate limit, schema contract, freshness SLO e recovery.
- `analyze platform-ecosystem` e `sparkforge_analyze_platform_ecosystem`.
- Radar Beam/DataHub/OpenMetadata explícito e opcional, fixtures, parity,
  surface lock, referências e knowledge.

## Gates rodados

- `python -m pytest tests/test_platform_ecosystem.py tests/test_fixtures_golden_platform.py -q --basetemp .sparkforge/local/pytest-platform-ecosystem` — `7 passed`, exit 0.
- `python -m sparkforge.adapters.cli analyze platform-ecosystem --path fixtures/platform/ecosystem.yaml` — exit 0.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .sparkforge/local/pytest-platform-ecosystem-gates` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge sdd check --repo . --feature DATA_PLATFORM_ECOSYSTEM` — `ok: true`.

## Limites e rollback

O inventário não prova saúde, compatibilidade, instalação, disponibilidade ou
adoção. O rollback é reverter os commits da feature em ordem inversa,
preservando os artefatos SDD.

## Lições

- Radar de interoperabilidade deve ser representado, mas permanecer separado
  de dependência runtime para evitar adoção inferida.
- Reliability Model é uma linguagem de contrato e precisa de evidência de
  operação antes de sustentar finding ou recomendação.
