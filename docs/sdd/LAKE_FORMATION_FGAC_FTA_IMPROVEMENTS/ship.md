---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS/build_report.md
  sha256: "d70be031b6b55cb32308b1a385b860ce3c41b9f8f0b659a1f73330e2726714b6"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, sync_skills, agents_parity, surface_lock, generated_reference, status_numbers_gate, claims_gate, rules_catalog_gates, routing_yaml, fixture_corpus_gates]
deviations:
  - "A matriz foi expandida apenas para células com fonte e limitação declaradas; combinações sem prova permanecem unknown ou version_dependent."
  - "Não houve chamada AWS, concessão de permissão, alteração de infraestrutura ou claim de custo/performance."
---

# LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS — entrega

## Hipótese

Confirmada no escopo offline: capability, topologia source/target,
cross-account, Hybrid Access, migração e semântica de IDs de catálogo são
avaliados separadamente e em modo fail-closed.

## Gates

- `python -m pytest tests/test_lakeformation_fgac_fta_improvements.py -q` — `8 passed`.
- `python -m pytest tests/test_dq_ai_unit.py tests/test_dq_ai_security.py tests/test_dq_ai_report.py tests/test_fixtures_golden_dq_ai.py tests/test_lakeformation_fgac_fta_improvements.py -q` — `19 passed`.
- Mirrors, referências, surface, bundle offline, claims e números correntes — registrados no build e sem provider call.
- `sparkforge sdd check --repo . --feature LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS` — `ok: true`.

## Entrega e limites

O decision engine preserva `unknown`, `limited` e `version_dependent` até
verificação específica; `not_supported` e escrita em `read_only` bloqueiam.
Glue ETL com `explicit_catalog_id`, Hybrid Access condicionado e Glue 4.0
corrente não são promovidos por analogia. Não há decisão operacional live.

## Rollback

Reverter commits da wave e regenerar referências, surface, locks e manifestos;
remover juntos as alterações de engine, knowledge, skills, agentes e fixtures.

## Lições

`glue.id` e `glue.account-id` respondem a perguntas diferentes. Source e target
também precisam de células independentes; aliasar dimensões produz decisões
aparentemente consistentes, mas sem evidência suficiente.
