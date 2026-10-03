---
sdd: 1
feature: STREAMING_MANAGED_FLINK_TEMPORAL_METRICS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_TEMPORAL_METRICS/build_report.md
  sha256: "dd4b92e3836367d3968ebdf8e0ea007a7efd45bb90579bedd48187e0a9f05bca"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, offline_manifest, sources_lock, surface_lock, generated_reference, status_numbers_gate]
deviations:
  - "O collector temporal reutiliza sparkforge_collect_managed_flink e não aumenta o número de tools."
  - "A suíte completa não foi executada; a validação ficou restrita ao feature, gates documentais e coleta de testes."
---

# STREAMING_MANAGED_FLINK_TEMPORAL_METRICS — entrega

## Hipótese

Confirmada no escopo declarado. A janela CloudWatch opcional produz observações
temporais application-level para Managed Flink, preserva missing/unresolved,
alimenta `managed_flink.metric`, mantém paridade CLI/MCP e repete pelo cache
sem nova chamada AWS. Isso não é conclusão de saúde, custo, causa, SLO,
throughput ou validação funcional.

## Gates rodados

- `python -m pytest tests/test_collect_managed_flink.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-feature` — **10 passed**.
- `python -m pytest tests/test_collect_managed_flink.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_status_numbers_gate.py tests/test_refresh_knowledge.py tests/test_offline_expansion.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-doc-gates2` — **161 passed**.
- `python -m pytest tests/ --collect-only -q -p no:cacheprovider` — **14492 tests collected**.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0, 0 divergências.
- `python scripts/check_status_numbers.py --strict` — exit 0, 0 divergências.
- `python scripts/refresh_knowledge.py --check --offline` — exit 0, 340 fontes.
- `python scripts/verify_offline_bundle.py --check` — exit 0, 69/69.
- `sparkforge sdd check --repo . --feature STREAMING_MANAGED_FLINK_TEMPORAL_METRICS` — exit 0.
- `git diff --check` — exit 0.

## Limites

O ship cobre somente cinco métricas de aplicação do namespace
`AWS/KinesisAnalytics`, dimensão `Application`, janela bounded, paginação,
normalização, analyzer e cache local. Task/Operator/Parallelism, custom e
connector metrics, job plan, savepoint, runtime/região/IAM/VPC efetivos,
histórico longo, replay, benchmark, SLO, saúde, causalidade, custo e escrita
AWS permanecem fora ou `unresolved`.
