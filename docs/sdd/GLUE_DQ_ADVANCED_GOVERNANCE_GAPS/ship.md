---
sdd: 1
feature: GLUE_DQ_ADVANCED_GOVERNANCE_GAPS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/GLUE_DQ_ADVANCED_GOVERNANCE_GAPS/build_report.md
  sha256: "c05ee1b553691eeb7202e50689330686ef1590bd2fd37a459cc063794674be9d"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, rules_catalog_gates, manifest_rule_count, fixture_corpus_gates, fixture_kind_coverage, reachability_lists, snippet_measure, runtime_scope_gates, agents_parity, generated_reference, surface_lock, status_numbers_gate]
deviations:
  - "O harness de thresholds exigiu subject metadata-only nos goldens; rows reais continuam recusados."
  - "Claims AWS, variabilidade, Iceberg e migração permanecem contexto documental; não há score, provider call ou geração de DQDL."
---

# GLUE_DQ_ADVANCED_GOVERNANCE_GAPS — entrega

## Hipótese

Confirmada no escopo offline: sampling, geografia e autorização aparecem como
estados determinísticos e separados; documentação não é promovida a observação,
e ausência de evidência continua `unresolved`.

## Gates

- DQ-AI unit/security/report/golden — `11 passed`.
- Catálogo, reachability, engine e result axis — `800 passed`.
- Agentes, router, docs, fixture coverage e refresh knowledge — `225 passed`.
- Threshold mutation, rule scope e runtime Glue — `675 passed`.
- Bundle offline — `57` entradas verificadas.
- `python -m pytest tests/test_dq_ai_unit.py tests/test_dq_ai_security.py tests/test_dq_ai_report.py tests/test_fixtures_golden_dq_ai.py -q` — `11 passed`.
- `sparkforge sdd check --repo . --feature GLUE_DQ_ADVANCED_GOVERNANCE_GAPS` — `ok: true`.

## Entrega e limites

Regras `SF-DQ-AI-006` a `SF-DQ-AI-008`, fixtures metadata-only, assessment e
report foram sincronizados com knowledge, locks e superfície. Nenhuma chamada
AWS, payload de rows, DQDL ou cálculo de custo/performance foi introduzido.

## Rollback

Reverter os commits desta wave em ordem inversa e remover em conjunto regras,
facts, fixtures, knowledge, locks e referências derivadas.

## Lições

Sampling, fronteira geográfica e cadeia de autorização precisam de evidências
separadas; um status documentado ou uma Region diferente não prova capacidade,
residência ou acesso.
