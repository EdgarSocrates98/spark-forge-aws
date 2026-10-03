---
sdd: 1
feature: STREAMING_KAFKA_TRANSPORT_EVIDENCE
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_KAFKA_TRANSPORT_EVIDENCE/build_report.md
  sha256: "7171df9dc571513485203270d1682eeb052ff2a0c8fa4d04c4b98ffab82b0520"
hypothesis_outcome: confirmed
registries: [rules_catalog_gates, manifest_rule_count, fixture_kind_coverage, runtime_scope_gates, reachability_lists, snippet_measure, fixture_corpus_gates, offline_manifest, sources_lock, sync_skills, agents_parity, surface_lock, generated_reference, status_numbers_gate]
deviations:
  - "O corpus revelou e corrigiu um golden Kinesis já desatualizado: kinesis.shard já emitia stream_name, mas o expected não o carregava."
  - "A superfície reutiliza sparkforge analyze transport e não cria collector live, tool ou verbo novo."
  - "A suíte completa não foi executada; os gates ficaram restritos ao contrato Kafka e às registries afetadas."
---

# STREAMING_KAFKA_TRANSPORT_EVIDENCE — entrega

## Hipótese

Confirmada no escopo declarado. Observações explícitas e timezone-aware produzem
`kafka.lag` e, quando suficientes e ordenáveis, `kafka.lag.series`; ISR abaixo
de replication factor produz `SF-STREAMOBS-003`; crescimento monotônico produz
`SF-STREAMOBS-004`. Snapshot legado não vira tendência, e nenhuma saída afirma
causa, saúde live, throughput, SLO, custo ou capacidade.

## Gates rodados

- `python -m pytest tests/test_facts_transport.py::test_kafka_explicit_lag_observations_emit_series_and_reject_insufficient tests/test_facts_transport.py::test_kafka_legacy_snapshot_does_not_infer_lag_series -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t1-green` — exit 0; T1 green.
- `python -m pytest tests/test_streaming_rules.py::test_kafka_transport_rules_require_observed_conditions -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t2-green` — exit 0; T2 green.
- `python -m pytest tests/test_fixtures_golden_transport.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t3-green` — **9 passed**.
- `python -m pytest tests/test_fixtures_kind_coverage.py::test_every_kind_of_every_extractor_appears_in_some_golden tests/test_fixtures_kind_coverage.py::test_every_rule_has_a_fixture_that_fires_it -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t3-coverage` — **61 passed**.
- `python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-ship-runtime` — **799 passed**.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-ship-extractor` — **954 passed**.
- `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-ship-fixtures` — **115 passed**.
- `python -m pytest tests/test_offline_expansion.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-ship-knowledge2` — **4 passed**.
- `python scripts/verify_offline_bundle.py` — exit 0; 69/69 documentos íntegros.
- `python scripts/refresh_knowledge.py --check --offline` — exit 0; 340 fontes.
- `python scripts/sync_skills.py --check` — exit 0.
- `python -m pytest tests/test_agent_coverage.py tests/test_agents_parity.py tests/test_sync_render.py tests/test_docs_coverage.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-ship-agents2` — **222 passed**.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0; zero divergências.
- `python scripts/check_status_numbers.py --strict` — exit 0; zero divergências.
- `sparkforge sdd check --repo . --feature STREAMING_KAFKA_TRANSPORT_EVIDENCE` — exit 0.
- `git diff --check` — exit 0.

## Red real antes do green

T1, T2, T3, T4 e T5 foram executadas com red real antes da correção. O primeiro
gate de conhecimento também detectou checksum stale em
`knowledge/transport-diagnostics.md`; o `knowledge/offline-manifest.json` foi
atualizado pelo hash normalizado e os gates foram repetidos com sucesso.

## Limites

O ship cobre fatos, composição temporal explícita, regras, goldens, cobertura de
kinds/regras, runtime scope, conhecimento offline, skills, mirrors, referências,
surface lock, números e SDD. Não cobre broker live, collector Kafka/MSK, REST,
CloudWatch, hot partition, causalidade, saúde, capacidade, SLO, custo, replay,
benchmark ou validação funcional.
