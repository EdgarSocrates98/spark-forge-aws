---
sdd: 1
feature: STREAMING_GLUE_SOURCE_SINK_ARTIFACTS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_GLUE_SOURCE_SINK_ARTIFACTS/build_report.md
  sha256: "d52805203d97eb0be231f407bf3c9c2930f4f57761fd4adbc5f85dd77a3d2800"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, generated_reference, surface_lock, reachability_lists, fixture_corpus_gates, fixture_kind_coverage, snippet_measure, sync_skills, agents_parity, status_numbers_gate]
deviations:
  - "Nenhuma regra, ferramenta CLI ou ferramenta MCP nova: o analyzer Glue Streaming existente foi reutilizado."
  - "Collector live, métricas temporais, throughput, exactly-once, capacidade e validação funcional permanecem fora do contrato offline."
---

# STREAMING_GLUE_SOURCE_SINK_ARTIFACTS — entrega

Entrega facts explícitos de source e sink para Glue Streaming, unresolved
fail-closed, corpus golden, knowledge, skill, guias, mirrors, offline manifest,
surface lock, status numbers e cobertura do prompt.

## Hipótese

Confirmada: dumps com endpoints produziram `glue.streaming.source` e
`glue.streaming.sink` com identidade e medidas observadas; dumps sem endpoints
produziram `source_metrics_missing`/`sink_metrics_missing`; campos ausentes não
viraram zero. As provas estão no build report e nos testes referenciados nos
ACs.

## Gates

- `python -m pytest tests/test_facts_glue_streaming.py -q --basetemp=...` — `6 passed`.
- `python -m pytest tests/test_fixtures_golden_glue_streaming.py tests/test_fixtures_kind_coverage.py -q --basetemp=...` — `73 passed`.
- Lote combinado facts/regras/goldens/analyzer/docs — `15 passed`.
- `python scripts/gen_reference_docs.py --check`.
- `python scripts/sync_skills.py --check`.
- `python scripts/check_status_numbers.py --strict`.
- `python scripts/verify_offline_bundle.py --check`.
- `python scripts/check_surface_lock.py`.
- `sparkforge sdd check --repo . --feature STREAMING_GLUE_SOURCE_SINK_ARTIFACTS`.
- Suíte completa não executada; permanece para fase explicitamente solicitada.

## Limites

Source/sink são observações de configuração, não prova de endpoint ativo,
backlog drain, latência, exactly-once, saúde, capacidade, custo ou resultado
funcional. A próxima wave pode adicionar composição temporal somente com
timestamps, identidade e baseline observados.
