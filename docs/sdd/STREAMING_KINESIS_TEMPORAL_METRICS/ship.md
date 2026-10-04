---
sdd: 1
feature: STREAMING_KINESIS_TEMPORAL_METRICS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_KINESIS_TEMPORAL_METRICS/build_report.md
  sha256: "23102e82527e2f4590df69675841920e832b8eccc2fb3e79182f1aa56738f77e"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, sources_lock, status_numbers_gate, reachability_lists, fixture_kind_coverage, snippet_measure]
deviations:
  - "A coleta reutiliza sparkforge_collect_streaming_integrations e não aumenta o número de tools."
---

# STREAMING_KINESIS_TEMPORAL_METRICS — entrega

## Hipótese

Os testes focados confirmam coleta, normalização, analyzer, paridade CLI/MCP e
limites documentais. A hipótese está confirmada no escopo stream-level
bounded; ausências continuam `unresolved` e a coleta não habilita métricas
enhanced nem infere saúde, causalidade, custo ou performance.

## Gates rodados

- `python -m pytest tests/test_collect_streaming.py tests/test_facts_transport.py tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py tests/test_harness_untrusted.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-gates` (963 passed, 1 preexistente gate drift corrigido)
- `python -m pytest tests/test_harness_untrusted.py::TestQuaisExtratoresCarregamTextoDeTerceiro::test_a_enumeracao_do_documento_bate_com_a_medida -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-snippet-green` (1 passed)
- `python scripts/gen_reference_docs.py --check` (exit 0)
- `python scripts/check_surface_lock.py` (exit 0)
- `python scripts/check_status_numbers.py --strict` (exit 0)
- `python scripts/refresh_knowledge.py --check --offline` (exit 0)
- `python scripts/verify_offline_bundle.py --check` (exit 0)
- `sparkforge sdd check --repo . --feature STREAMING_KINESIS_TEMPORAL_METRICS` (exit 0)

## Limites

Este ship não cobre enhanced/shard-level metrics, reshard history, KCL/EFO,
Kafka Connect, Kafka Streams, OpenLineage, replay, causalidade, SLO automático,
benchmark, custo ou execução live.
