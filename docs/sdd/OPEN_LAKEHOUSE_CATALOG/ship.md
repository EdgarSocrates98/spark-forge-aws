---
sdd: 1
feature: OPEN_LAKEHOUSE_CATALOG
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/OPEN_LAKEHOUSE_CATALOG/build_report.md
  sha256: "20ef9c742907f26906a70401525981d2236498eb0027a1449132fa0c5bced535"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, surface_lock, generated_reference, offline_manifest, sources_lock]
deviations:
  - "T1–T3 não registraram red/green porque a implementação precede o build_report; nenhum exit vermelho foi inventado."
  - "A validação direcionada usou basetemp dentro do workspace devido ao WinError 5 no TEMP padrão do host."
---

# OPEN_LAKEHOUSE_CATALOG — entrega

## Hipótese

Confirmada no escopo offline. O contrato comum representa Glue Catalog,
Iceberg REST, Polaris, S3 Tables, Lake Formation e integrações futuras como
identidades declaradas; engines e bindings preservam evidence, fingerprint e
unresolved sem presumir compatibilidade ou executar protocolo live.

## O que foi entregue

- Contrato `contracts/lakehouse-catalog-v1.schema.json` e fixture sintético
  multi-catalog/multi-engine.
- Loader com fingerprint canônico, sanitização de secrets, capabilities e
  referências unresolved.
- `analyze lakehouse-catalog` e `sparkforge_analyze_lakehouse_catalog` usando
  o mesmo núcleo.
- Parity, surface lock, referências geradas e documentação operacional.

## Gates rodados

- `python -m pytest tests/test_lakehouse_catalog.py -q --basetemp .sparkforge_aws/local/pytest-open-lakehouse` — `3 passed`, exit 0.
- `python -m sparkforge_aws.adapters.cli analyze lakehouse-catalog --path fixtures/platform/catalog.yaml` — exit 0.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .sparkforge_aws/local/pytest-open-lakehouse-gates` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge-aws sdd check --repo . --feature OPEN_LAKEHOUSE_CATALOG` — `ok: true`.

## Limites e rollback

O analisador não descobre credenciais, não negocia protocolo e não cria,
altera ou exclui catalog, tabela, bucket ou grant. O rollback é reverter os
commits da feature em ordem inversa, mantendo os artefatos SDD para auditoria.

## Lições

- Catalog topology deve ser ligada ao Metadata Graph por IDs e evidence, nunca
  por nomes parecidos de tabelas.
- Future live adapters precisam trazer runtime version, freshness e evidence
  antes de transformar declaração em capacidade observada.
