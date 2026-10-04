---
sdd: 1
feature: STREAMING_FLINK_SOURCE_SINK_ARTIFACTS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_FLINK_SOURCE_SINK_ARTIFACTS/build_report.md
  sha256: "f65f9481b99c1a49a9ff97032186dc529d3bf790af70d230759504e6cec0091a"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, surface_lock, reachability_lists, fixture_kind_coverage, snippet_measure, fixture_corpus_gates, sync_skills, agents_parity, status_numbers_gate]
deviations:
  - "Nenhuma regra, tool CLI ou tool MCP nova: o analyzer Flink existente foi reutilizado."
  - "Runtime observado, savepoints, métricas temporais, throughput, exactly-once e validação funcional permanecem fora do contrato offline."
---

# STREAMING_FLINK_SOURCE_SINK_ARTIFACTS — entrega

Entrega facts explícitos de source e sink para Apache Flink, unresolved
fail-closed, corpus golden regenerado, knowledge, skill, guias, mirrors,
manifest offline e cobertura do prompt. Managed Flink permanece em namespace
separado.

## Hipótese

Confirmada: dumps com endpoints produziram `flink.source`/`flink.sink` com
identidade e medidas observadas; dumps sem endpoints produziram
`source_metrics_missing`/`sink_metrics_missing`; campos ausentes não viraram
zero. As provas estão no build report e nos testes referenciados nos ACs.

## Gates

- `python -m pytest tests/test_facts_flink.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-flink` — `8 passed`.
- `python -m pytest tests/test_facts_flink.py tests/test_fixtures_golden_flink.py tests/test_fixtures_kind_coverage.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-flink-golden` — `83 passed`.
- `python -m pytest tests/test_docs_coverage.py::test_flink_source_sink_artifacts_coverage -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-flink-docs` — passed.
- `python scripts/gen_reference_docs.py --check`.
- `python scripts/sync_skills.py --check`.
- `python scripts/check_status_numbers.py --strict`.
- `python scripts/verify_offline_bundle.py --check`.
- `python scripts/check_surface_lock.py`.
- `sparkforge sdd check --repo . --feature STREAMING_FLINK_SOURCE_SINK_ARTIFACTS`.
- Suíte completa não executada; permanece para uma fase explicitamente solicitada.

## Limites

Source/sink são evidência de dump, não prova de throughput, backlog drain,
latência, exatamente-once, saúde, capacidade ou correção funcional. A próxima
wave pode adicionar uma composição temporal somente com runtime, timestamps,
identidade e baseline observados.
